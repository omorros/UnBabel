"""Push-to-talk mic capture. Record between start() and stop(); return a 16kHz mono float32
numpy array ready for Whisper.

Callback-based on purpose: sd.InputStream runs the callback on PortAudio's own high-priority
thread, and start()/stop() are near-instant, so this never blocks an asyncio event loop when it
lands in offbabel/server.py. Only the heavy Whisper call needs a worker thread (see stt.py).

Standalone test:  python -m speech_to_agent.record      (lists mics, records 3s, prints level)
"""
import math

import numpy as np
import sounddevice as sd

try:
    from scipy.signal import resample_poly
except Exception:  # noqa: BLE001
    resample_poly = None

from . import config


def list_inputs():
    """Print input-capable devices so you can pick OFFBABEL_MIC (index or name)."""
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            print(f"  [{i}] {d['name']}  "
                  f"({d['max_input_channels']}ch @ {int(d['default_samplerate'])}Hz)")


def _native_sr(device):
    info = sd.query_devices(device, "input") if device is not None else sd.query_devices(kind="input")
    return int(info["default_samplerate"])


def _dev_name(device):
    try:
        return sd.query_devices(device, "input")["name"]
    except Exception:  # noqa: BLE001
        return str(device) if device is not None else "system default"


def _preferred_input():
    """With no device forced, prefer the built-in mic. Bluetooth inputs (AirPods) frequently
    deliver only silence/zero blocks over PortAudio — the #1 cause of 'heard nothing'. Returns a
    device name to use, or None to fall back to the system default."""
    try:
        builtin = [d["name"] for d in sd.query_devices()
                   if d["max_input_channels"] > 0 and "MacBook" in d["name"] and "Microphone" in d["name"]]
        return builtin[0] if builtin else None
    except Exception:  # noqa: BLE001
        return None


def _bad_input_msg(device, what):
    return (f"Mic problem ({what}) on input '{_dev_name(device)}'.\n"
            f"  - If this is a Bluetooth device (e.g. AirPods), use the built-in mic:\n"
            f"      OFFBABEL_MIC='MacBook Pro Microphone'   (or System Settings > Sound > Input)\n"
            f"  - Otherwise grant Microphone access to your terminal/IDE in\n"
            f"      System Settings > Privacy & Security > Microphone.")


class PTTRecorder:
    """start() on speak_ptt_start, stop() on speak_ptt_stop. Records at the device's native
    rate and resamples to 16kHz on stop()."""

    def __init__(self, device=None):
        # explicit arg > OFFBABEL_MIC > built-in mic > system default
        if device is None:
            device = config.MIC_DEVICE if config.MIC_DEVICE is not None else _preferred_input()
        self.device = device
        self.native_sr = _native_sr(device)
        self._stream = None
        self._blocks = []
        print(f"[mic] input: {_dev_name(device)} @ {self.native_sr}Hz", flush=True)

    def _callback(self, indata, frames, time, status):
        if status:
            print("audio status:", status, flush=True)  # log out-of-band; never block in here
        self._blocks.append(indata.copy())              # MUST copy: PortAudio reuses the buffer

    def start(self):
        self._blocks = []
        self._stream = sd.InputStream(samplerate=self.native_sr, device=self.device,
                                      channels=1, dtype="float32", callback=self._callback)
        self._stream.start()

    def stop(self):
        """Stop and return float32 mono 16kHz audio. Raises if the capture is silent (the
        classic macOS mic-permission failure)."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._blocks:
            raise RuntimeError(_bad_input_msg(self.device, "no audio blocks"))
        audio = np.concatenate(self._blocks, axis=0)[:, 0]   # (N,1) -> (N,)
        audio = _resample(audio, self.native_sr, config.TARGET_SR)
        return _normalize(audio, self.device)


def _resample(audio, src_sr, dst_sr):
    if src_sr == dst_sr or audio.size == 0:
        return audio.astype(np.float32, copy=False)
    if resample_poly is None:
        raise RuntimeError(f"scipy needed to resample {src_sr}->{dst_sr}Hz (pip install scipy)")
    g = math.gcd(src_sr, dst_sr)                          # 48000->16000 = up 1, down 3
    return resample_poly(audio, dst_sr // g, src_sr // g).astype(np.float32, copy=False)


def _normalize(audio, device=None):
    if audio.size == 0:
        return audio
    peak = float(np.max(np.abs(audio)))
    if peak < 1e-4:  # zeros: denied mic permission OR a Bluetooth input delivering silence
        raise RuntimeError(_bad_input_msg(device, "captured silence"))
    if peak < 0.95:  # peak-normalize quiet short utterances so Whisper has signal
        audio = audio * (0.95 / peak)
    return audio.astype(np.float32, copy=False)


def main():
    import time
    print("Input devices:")
    list_inputs()
    dev = config.MIC_DEVICE if config.MIC_DEVICE is not None else "default"
    print(f"\nRecording 3s on device {dev} ...")
    rec = PTTRecorder()
    rec.start()
    time.sleep(3.0)
    audio = rec.stop()
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    print(f"captured {audio.size} samples @ {config.TARGET_SR}Hz  peak={peak:.3f}  "
          f"({audio.size / config.TARGET_SR:.1f}s)")


if __name__ == "__main__":
    main()
