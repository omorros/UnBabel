"""Live BSL letter detection with debounce — standalone test of the trained classifier.

Run:  python -m offbabel.sign.live

This is the 12:30 GATE check: if it reliably distinguishes >=5 letters under venue light,
we go full dual-mode. If it flaps, we pivot to Speak-only (PRD section 8).
"""
import collections

import cv2
import joblib
import numpy as np
import mediapipe as mp

from .landmarks import build_feature_vector
from .capture import extract_hands
from .. import config


def predict(bundle, feat):
    clf = bundle["model"]
    proba = clf.predict_proba([feat])[0]
    i = int(np.argmax(proba))
    return clf.classes_[i], float(proba[i])


def main():
    bundle = joblib.load(config.SIGN_MODEL_PATH)
    recent = collections.deque(maxlen=config.DEBOUNCE_FRAMES)
    mp_hands = mp.solutions.hands

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    with mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.6,
                        min_tracking_confidence=0.5) as model:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            results = model.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            hands = extract_hands(results)

            label, conf = "-", 0.0
            if hands:
                label, conf = predict(bundle, build_feature_vector(hands))
                recent.append(label if conf >= config.CONF_THRESHOLD else None)
            else:
                recent.append(None)

            # accepted only when the whole debounce window agrees on a real (non-negative) letter
            stable = None
            if len(recent) == recent.maxlen and len(set(recent)) == 1:
                only = recent[0]
                if only and only != config.NEG_LABEL:
                    stable = only

            color = (0, 220, 0) if stable else (0, 180, 220)
            msg = f"{label} {conf:.2f}"
            msg += f"   ===> {stable}" if stable else "   (hold steady...)"
            cv2.putText(frame, msg, (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.imshow("OffBabel sign  [q quit]", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
