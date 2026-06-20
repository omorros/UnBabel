"""Capture normalized BSL landmark samples from the webcam, labeled live.

Run:  python -m offbabel.sign.capture     (from the repo root)

Controls:
  a-z    arm that letter -> every frame with hand(s) visible is saved as that letter
  0      arm the negative "nothing" class (junk / no clear sign) -> rejects noise later
  SPACE  disarm (stop saving)
  u      undo last sample
  q      quit + write data/landmarks.csv

Protocol (PRD section 4): ~30-50 samples/letter, BOTH hands in frame, slight natural
variation in angle/distance, UNDER VENUE LIGHTING, plain background. Hold the shape and
stay armed for ~2s to collect a burst. Make H, E, L, O rock-solid; test E-vs-O hardest.
"""
import csv
import os

import cv2
import mediapipe as mp

from .landmarks import build_feature_vector, FEATURE_DIM
from .. import config

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils


def extract_hands(results):
    """MediaPipe results -> list of ('Left'|'Right', [(x,y,z)*21])."""
    hands = []
    if results.multi_hand_landmarks and results.multi_handedness:
        for lm, handed in zip(results.multi_hand_landmarks, results.multi_handedness):
            label = handed.classification[0].label  # 'Left' or 'Right'
            pts = [(p.x, p.y, p.z) for p in lm.landmark]
            hands.append((label, pts))
    return hands


def main():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    rows = []           # each: [f0..f125, label]
    armed = None        # currently-armed label, or None

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    with mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.6,
                        min_tracking_confidence=0.5) as model:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)  # mirror for natural interaction
            results = model.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            hands = extract_hands(results)

            if results.multi_hand_landmarks:
                for lm in results.multi_hand_landmarks:
                    mp_draw.draw_landmarks(frame, lm, mp_hands.HAND_CONNECTIONS)

            # save while armed and at least one hand is visible
            if armed is not None and hands:
                rows.append(list(build_feature_vector(hands)) + [armed])

            counts = {}
            for r in rows:
                counts[r[-1]] = counts.get(r[-1], 0) + 1
            hud = f"ARMED:{armed}  total:{len(rows)}  hands:{len(hands)}"
            cv2.putText(frame, hud, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame, str(counts), (10, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 0), 1)
            cv2.imshow("OffBabel capture  [a-z arm | 0 neg | SPACE stop | u undo | q quit]", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord(" "):
                armed = None
            elif key == ord("u"):
                if rows:
                    rows.pop()
            elif key == ord("0"):
                armed = config.NEG_LABEL
            elif 97 <= key <= 122:  # a-z
                armed = chr(key).upper()

    cap.release()
    cv2.destroyAllWindows()

    with open(config.LANDMARKS_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([f"f{i}" for i in range(FEATURE_DIM)] + ["label"])
        w.writerows(rows)
    print(f"Wrote {len(rows)} samples to {config.LANDMARKS_CSV}")
    if rows:
        from collections import Counter
        print("Per-label counts:", dict(Counter(r[-1] for r in rows)))


if __name__ == "__main__":
    main()
