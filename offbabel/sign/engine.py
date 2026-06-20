"""Background webcam -> MediaPipe -> KNN recognition that streams detections to the UI.

The OpenCV loop is blocking, so it runs in a thread and pushes JSON events onto the server's
asyncio loop via run_coroutine_threadsafe. Vision deps are lazy-imported inside the thread so
the server still boots on a machine without them (UI dev on a box with no mediapipe).
"""
import asyncio
import collections
import threading

from .. import config, memory


class SignEngine:
    def __init__(self):
        self._thread = None
        self._stop = threading.Event()

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, loop, emit):
        """loop: the server asyncio loop. emit: a coroutine function taking one dict (hub.send)."""
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, args=(loop, emit), daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _emit(self, loop, emit, msg):
        try:
            asyncio.run_coroutine_threadsafe(emit(msg), loop)
        except Exception:  # noqa: BLE001
            pass

    def _run(self, loop, emit):
        try:
            import cv2
            import joblib
            import numpy as np
            from .hands import create_landmarker, detect, to_hands
            from .landmarks import build_feature_vector
        except Exception as e:  # noqa: BLE001
            self._emit(loop, emit, {"type": "status", "sign_error": f"vision deps missing: {e}"})
            return

        try:
            bundle = joblib.load(config.SIGN_MODEL_PATH)
        except Exception as e:  # noqa: BLE001
            self._emit(loop, emit, {"type": "status", "sign_error": f"no trained model yet: {e}"})
            return

        clf = bundle["model"]
        recent = collections.deque(maxlen=config.DEBOUNCE_FRAMES)
        last_stable = None
        landmarker = create_landmarker()
        cap = cv2.VideoCapture(config.CAMERA_INDEX)

        try:
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    break
                frame = cv2.flip(frame, 1)
                hands = to_hands(detect(landmarker, frame))

                label, conf = "-", 0.0
                if hands:
                    feat = build_feature_vector(hands)
                    proba = clf.predict_proba([feat])[0]
                    i = int(np.argmax(proba))
                    label, conf = str(clf.classes_[i]), float(proba[i])
                    recent.append(label if conf >= config.CONF_THRESHOLD else None)
                else:
                    recent.append(None)

                stable = None
                if len(recent) == recent.maxlen and len(set(recent)) == 1:
                    only = recent[0]
                    if only and only != config.NEG_LABEL:
                        stable = only

                self._emit(loop, emit, {
                    "type": "sign_detect",
                    "label": stable or label,
                    "confidence": conf,
                    "stable": bool(stable),
                })

                # count each newly-recognized sign once (memory / progress)
                if stable and stable != last_stable:
                    last_stable = stable
                    memory.log_seen("sign", "bsl", stable)
                elif not stable:
                    last_stable = None
        finally:
            cap.release()
            landmarker.close()
