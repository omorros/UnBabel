"""Reachy "speak" output leg: make Reachy Mini say a line, with antenna wobble while it talks.

    say_reachy("Hello!", language="en")
    say_reachy("Hola, soy Reachy Mini.", language="es")

Pipeline:  text -> macOS `say` -> speech.aiff -> ffmpeg -> reachy_speech.wav
           -> upload to the Reachy daemon -> enable wobbling -> play -> wait -> disable wobbling

This is the tutor's VOICE for OffBabel Speak: the agent produces a reply, this speaks it through
the robot. Reachy is conversational output + presence; audio INPUT comes from the Mac mic (the
robot-mic->STT path was too slow). The on-screen avatar can mirror the same speaking state so the
demo still works if the robot drops (PRD: robot = enhancement, not dependency).

Requirements:
  pip install requests          (in the spike venv)
  brew install ffmpeg           (provides ffmpeg + ffprobe)
  macOS `say` is built in.
  The Reachy daemon API must be reachable at api_base (default http://localhost:8000) — keep an
  SSH tunnel open:  ssh -N -L 8000:127.0.0.1:8000 pollen@reachy-mini.local
"""
from __future__ import annotations

import json
import math
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Literal

import requests


Language = Literal["en", "es"]


DEFAULT_VOICES: dict[str, str] = {
    "en": "Samantha",
    # Change this if your Mac uses a different Spanish voice.
    # Check available voices with: say -v '?'   (Czech bonus: "Zuzana")
    "es": "Mónica",
}


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _audio_duration_seconds(path: Path) -> float:
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ]
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def set_reachy_volume(api_base: str, volume: int = 100) -> None:
    volume = max(0, min(100, volume))
    requests.post(
        f"{api_base}/api/volume/set",
        json={"volume": volume},
        timeout=10,
    ).raise_for_status()


def upload_sound(api_base: str, wav_path: Path, remote_filename: str = "reachy_speech.wav") -> None:
    # The daemon stores uploaded files by original filename, so use a stable filename.
    upload_path = wav_path.with_name(remote_filename)
    if upload_path != wav_path:
        upload_path.write_bytes(wav_path.read_bytes())

    with upload_path.open("rb") as f:
        response = requests.post(
            f"{api_base}/api/media/sounds/upload",
            files={"file": (remote_filename, f, "audio/wav")},
            timeout=60,
        )
    response.raise_for_status()


def play_sound(api_base: str, remote_filename: str = "reachy_speech.wav") -> None:
    response = requests.post(
        f"{api_base}/api/media/play_sound",
        json={"file": remote_filename},
        timeout=10,
    )
    response.raise_for_status()


def set_wobbling(api_base: str, enabled: bool) -> None:
    endpoint = "enable" if enabled else "disable"
    requests.post(
        f"{api_base}/api/media/wobbling/{endpoint}",
        timeout=10,
    ).raise_for_status()


def synthesize_to_wav(
    text: str,
    wav_path: Path,
    *,
    language: Language = "en",
    voice: str | None = None,
    gain: float = 2.0,
) -> float:
    voice = voice or DEFAULT_VOICES.get(language, "Samantha")

    with tempfile.TemporaryDirectory() as tmpdir:
        aiff_path = Path(tmpdir) / "speech.aiff"

        # macOS built-in TTS.
        _run(["say", "-v", voice, "-o", str(aiff_path), text])

        # Convert to Reachy-friendly WAV and optionally boost volume.
        _run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(aiff_path),
                "-af",
                f"volume={gain}",
                "-ac",
                "2",
                "-ar",
                "48000",
                "-sample_fmt",
                "s16",
                str(wav_path),
            ]
        )

    return _audio_duration_seconds(wav_path)


def say_reachy(
    text: str,
    *,
    language: Language = "en",
    api_base: str = "http://localhost:8000",
    voice: str | None = None,
    volume: int = 100,
    gain: float = 2.0,
    wobble: bool = True,
    wait: bool = True,
    remote_filename: str = "reachy_speech.wav",
    output_dir: str | Path = "~/reachy-tts",
) -> float:
    """
    Speak text through Reachy Mini's daemon speaker path.

    Returns:
        Audio duration in seconds.
    """
    output_dir = Path(output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    wav_path = output_dir / remote_filename

    duration = synthesize_to_wav(
        text,
        wav_path,
        language=language,
        voice=voice,
        gain=gain,
    )

    set_reachy_volume(api_base, volume)
    upload_sound(api_base, wav_path, remote_filename)

    try:
        if wobble:
            set_wobbling(api_base, True)

        play_sound(api_base, remote_filename)

        if wait:
            time.sleep(math.ceil(duration) + 0.5)

    finally:
        if wobble:
            try:
                set_wobbling(api_base, False)
            except Exception:
                pass

    return duration


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Make Reachy Mini speak text.")
    parser.add_argument("text", help="Text to speak")
    parser.add_argument("--language", choices=["en", "es"], default="en")
    parser.add_argument("--voice", default=None)
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument("--volume", type=int, default=100)
    parser.add_argument("--gain", type=float, default=2.0)
    parser.add_argument("--no-wobble", action="store_true")
    parser.add_argument("--no-wait", action="store_true")

    args = parser.parse_args()

    duration = say_reachy(
        args.text,
        language=args.language,
        api_base=args.api_base,
        voice=args.voice,
        volume=args.volume,
        gain=args.gain,
        wobble=not args.no_wobble,
        wait=not args.no_wait,
    )

    print(f"Played {duration:.2f}s of speech.")
