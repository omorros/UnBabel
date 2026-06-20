"""Background webcam -> MediaPipe -> KNN recognition that streams detections to the UI.

The OpenCV loop is blocking, so it runs in a thread and pushes JSON events onto the server's
asyncio loop via run_coroutine_threadsafe. Vision deps are lazy-imported inside the thread so
the server still boots on a machine without them (UI dev on a box with no mediapipe).
"""
import asyncio
import collections
import threading
import time

from .. import config, srs


class SignEngine:
    def __init__(self):
        self._thread = None
        self._stop = threading.Event()
        self._level = "L3"

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, loop, emit, level="L3"):
        """loop: the server asyncio loop. emit: a coroutine function taking one dict (hub.send)."""
        if self.running:
            return
        self._level = level or "L3"
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

        # Prefer the Reachy camera — the same feed the Sign screen shows — so recognition runs on the
        # exact video the user sees. Registering as a stream client keeps rpicam running and shares
        # the one SSH stream with the browser <img> via the streamer's refcount. Fall back to the
        # local webcam if the robot feed never produces a frame (laptop-only dev, robot offline).
        from ..reachy_video import streamer as reachy
        reachy.add_client()
        use_reachy = self._wait_for_first_frame(reachy)
        cap = None
        if not use_reachy:
            reachy.remove_client()
            cap = cv2.VideoCapture(config.CAMERA_INDEX)
        self._emit(loop, emit, {"type": "status", "sign_source": "reachy" if use_reachy else "webcam"})

        last_jpeg = None
        try:
            while not self._stop.is_set():
                if use_reachy:
                    jpeg = reachy.get_latest_frame()
                    if jpeg is None or jpeg is last_jpeg:  # no new frame yet; yield without spinning
                        if self._stop.wait(0.02):
                            break
                        continue
                    last_jpeg = jpeg
                    frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
                    if frame is None:
                        continue
                else:
                    ok, frame = cap.read()
                    if not ok:
                        break
                frame = cv2.flip(frame, 1)  # match the mirrored frames the model was trained on
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

                # count each newly-recognized sign once (spaced repetition + live progress)
                if stable and stable != last_stable:
                    last_stable = stable
                    srs.record_result("sign", self._level, self._level, stable, True)
                    self._emit(loop, emit, {"type": "summary", "summary": srs.summary()})
                elif not stable:
                    last_stable = None
        finally:
            if use_reachy:
                reachy.remove_client()  # last viewer leaving stops the shared SSH stream
            if cap is not None:
                cap.release()
            landmarker.close()

    def _wait_for_first_frame(self, reachy, timeout=4.0):
        """Give the Reachy stream a moment to deliver its first JPEG. Returns True if a frame
        arrived within the timeout, False so the caller can fall back to the local webcam."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not self._stop.is_set():
            if reachy.get_latest_frame() is not None:
                return True
            self._stop.wait(0.1)
        return False
