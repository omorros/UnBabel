"""Capture normalized BSL landmark samples from the webcam.

GUIDED mode (recommended) - it tells you which letter to show and auto-collects samples:
    python -m offbabel.sign.capture --letters A,E,I,O,U --per 35
    python -m offbabel.sign.capture --letters B,C,L,R,T --per 35 --append
  Hold each handshape (both hands in frame). It collects while you hold, then moves to the next
  letter automatically. Keys: n = skip to next, u = undo last, q = quit + save.

FREE mode (no --letters) - arm a label yourself:
    python -m offbabel.sign.capture
  Keys: a-z arm a letter, 0 arm negative/"nothing", SPACE stop, u undo, q quit + save.

Protocol (PRD section 4): ~30-50 samples/letter, BOTH hands in frame, slight natural variation
in angle/distance, UNDER VENUE LIGHTING, plain background. BSL is two-handed.
"""
import argparse
import csv
import os
from collections import Counter

import cv2

from .hands import create_landmarker, detect, to_hands, draw
from .landmarks import build_feature_vector, FEATURE_DIM
from .. import config


def _load_existing():
    rows = []
    if os.path.exists(config.LANDMARKS_CSV):
        with open(config.LANDMARKS_CSV, newline="") as f:
            r = csv.reader(f)
            next(r, None)  # header
            for row in r:
                if len(row) == FEATURE_DIM + 1:
                    rows.append([float(x) for x in row[:FEATURE_DIM]] + [row[FEATURE_DIM]])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--letters", help="comma list to guide capture, e.g. A,E,I,O,U")
    ap.add_argument("--per", type=int, default=35, help="target samples per letter (guided)")
    ap.add_argument("--append", action="store_true", help="append to existing landmarks.csv")
    args = ap.parse_args()

    guided = [s.strip().upper() for s in args.letters.split(",")] if args.letters else None
    os.makedirs(config.DATA_DIR, exist_ok=True)

    rows = _load_existing() if args.append else []
    counts = Counter(r[-1] for r in rows)
    armed = None        # free mode
    frame_no = 0
    cur_target = None   # guided: the letter currently being collected
    grace = 0           # guided: countdown frames before collecting a NEW letter (time to switch shape)
    GRACE_FRAMES = 45   # ~1.5s at 30fps

    landmarker = create_landmarker()
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            frame_no += 1
            result = detect(landmarker, frame)
            hands = to_hands(result)
            draw(frame, result)

            if guided:
                target = next((c for c in guided if counts[c] < args.per), None)
                if target != cur_target:          # switched letters -> grace period to change shape
                    cur_target = target
                    grace = GRACE_FRAMES if target else 0
                if target and grace > 0:
                    grace -= 1
                    hud = f"GET READY: {target}   {grace / 30.0:0.1f}s"
                    color = (0, 140, 220)
                elif target:
                    # collect every 3rd frame so a held pose yields varied samples
                    if hands and frame_no % 3 == 0:
                        rows.append(list(build_feature_vector(hands)) + [target])
                        counts[target] += 1
                    hud = f"SHOW: {target}   {counts[target]}/{args.per}"
                    color = (0, 220, 0) if hands else (0, 140, 220)
                else:
                    hud = "DONE - press q to save"
                    color = (0, 220, 0)
                cv2.putText(frame, hud, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
                prog = " ".join(f"{c}:{counts[c]}" for c in guided)
                cv2.putText(frame, prog, (10, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 0), 1)
            else:
                if armed is not None and hands:
                    rows.append(list(build_feature_vector(hands)) + [armed])
                    counts[armed] += 1
                cv2.putText(frame, f"ARMED:{armed}  total:{len(rows)}", (10, 32),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, str(dict(counts)), (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 0), 1)

            cv2.imshow("OffBabel capture  [q save | u undo | n next | a-z/0 arm (free)]", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("u") and rows:
                counts[rows[-1][-1]] -= 1
                rows.pop()
            elif guided and key == ord("n"):
                # skip current target: fill its count so it advances
                tgt = next((c for c in guided if counts[c] < args.per), None)
                if tgt:
                    counts[tgt] = args.per
            elif not guided:
                if key == ord(" "):
                    armed = None
                elif key == ord("0"):
                    armed = config.NEG_LABEL
                elif 97 <= key <= 122:
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
    print("Per-label counts:", dict(counts))


if __name__ == "__main__":
    main()
