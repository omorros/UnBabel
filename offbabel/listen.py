"""Hands-free microphone listener for Speak. Energy-based voice activity detection: captures the
laptop mic, buffers while you talk, and when you pause (~0.8s silence) it transcribes the
utterance (faster-whisper) and hands the text to a callback. Runs the blocking audio loop in a
thread; lazy-imports audio deps so the server still boots without them.

Tune the threshold for the room with OFFBABEL_MIC_THRESHOLD (higher = needs louder speech).
"""
import os
import threading

SAMPLE_RATE = 16000
BLOCK_SEC = 0.03  # 30 ms blocks


class SpeakListener:
    def __init__(self):
        self._thread = None
        self._stop = threading.Event()

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, on_utterance, language="es", on_speech_end=None):
        """on_utterance(text) is called after each detected utterance (text may be "" if STT found
        nothing). on_speech_end() fires the moment speech ends, BEFORE transcription — use it to
        start the 'thinking' motion so the robot reacts during the STT+LLM gap, not after it."""
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, args=(on_utterance, language, on_speech_end), daemon=True
        )
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self, on_utterance, language, on_speech_end=None):
        try:
            import numpy as np
            import sounddevice as sd
            from . import speak
            from speech_to_agent.record import _preferred_input
        except Exception as e:  # noqa: BLE001
            print("mic listener deps missing:", e)
            return

        device = _preferred_input()  # built-in mic; avoids the AirPods-zeros default (None = system default)
        block = int(SAMPLE_RATE * BLOCK_SEC)
        threshold = float(os.environ.get("OFFBABEL_MIC_THRESHOLD", "0.015"))
        sil_limit = int(0.8 / BLOCK_SEC)   # ~0.8s of silence ends an utterance
        min_speech = int(0.3 / BLOCK_SEC)  # need at least ~0.3s of speech
        buf = []
        speaking = False
        silence = 0

        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                                blocksize=block, device=device) as stream:
                while not self._stop.is_set():
                    data, _ = stream.read(block)
                    chunk = data[:, 0]
                    energy = float(np.sqrt(np.mean(chunk ** 2)))
                    if energy > threshold:
                        speaking = True
                        silence = 0
                        buf.append(chunk.copy())
                    elif speaking:
                        buf.append(chunk.copy())
                        silence += 1
                        if silence >= sil_limit:
                            audio = np.concatenate(buf)
                            buf, speaking, silence = [], False, 0
                            if len(audio) >= min_speech * block:
                                if on_speech_end:
                                    try:
                                        on_speech_end()  # start 'thinking' motion now (covers STT+LLM)
                                    except Exception:  # noqa: BLE001
                                        pass
                                try:
                                    text = speak.transcribe(audio, language)
                                except Exception as e:  # noqa: BLE001
                                    print("transcribe failed:", e)
                                    text = ""
                                on_utterance(text)  # always call; server stops the motion if text is empty
        except Exception as e:  # noqa: BLE001
            print("mic listener stopped:", e)
