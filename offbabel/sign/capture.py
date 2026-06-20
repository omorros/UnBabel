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

from .hands import create_landmarker, detect, to_hands, draw
from .landmarks import build_feature_vector, FEATURE_DIM
from .. import config


def main():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    rows = []           # each: [f0..f125, label]
    armed = None        # currently-armed label, or None

    landmarker = create_landmarker()
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)  # mirror for natural interaction
            result = detect(landmarker, frame)
            hands = to_hands(result)
            draw(frame, result)

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
    finally:
        cap.release()
        cv2.destroyAllWindows()
        landmarker.close()

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
