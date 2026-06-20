"""MediaPipe hand detection, centralized. The legacy `mp.solutions.hands` API was removed in
mediapipe 0.10.x, so we use the Tasks `HandLandmarker` with a vendored model file. capture,
live, and engine all go through here so there is one code path and one place to change.

IMAGE running mode (per-frame, no timestamp bookkeeping); we do our own debounce downstream.
"""
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from .. import config

# 21 landmark connections for drawing (MediaPipe hand topology)
_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),          # index
    (5, 9), (9, 10), (10, 11), (11, 12),     # middle
    (9, 13), (13, 14), (14, 15), (15, 16),   # ring
    (13, 17), (17, 18), (18, 19), (19, 20),  # little
    (0, 17),                                  # palm base
]


def create_landmarker():
    base = mp_python.BaseOptions(model_asset_path=config.HAND_MODEL_PATH)
    opts = vision.HandLandmarkerOptions(
        base_options=base,
        num_hands=2,
        running_mode=vision.RunningMode.IMAGE,
    )
    return vision.HandLandmarker.create_from_options(opts)


def detect(landmarker, frame_bgr):
    """Run detection on a BGR frame. Returns the raw HandLandmarkerResult."""
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    return landmarker.detect(mp_image)


def to_hands(result):
    """Result -> list of ('Left'|'Right', [(x, y, z) * 21]). Consistent ordering downstream."""
    hands = []
    if result and result.hand_landmarks:
        for i, lms in enumerate(result.hand_landmarks):
            label = "Right"
            if result.handedness and i < len(result.handedness) and result.handedness[i]:
                label = result.handedness[i][0].category_name
            pts = [(p.x, p.y, p.z) for p in lms]
            hands.append((label, pts))
    return hands


def draw(frame_bgr, result):
    """Draw landmark dots + connections onto the frame (replaces the old drawing_utils)."""
    if not result or not result.hand_landmarks:
        return
    h, w = frame_bgr.shape[:2]
    for lms in result.hand_landmarks:
        px = [(int(p.x * w), int(p.y * h)) for p in lms]
        for a, b in _CONNECTIONS:
            cv2.line(frame_bgr, px[a], px[b], (0, 180, 120), 2)
        for x, y in px:
            cv2.circle(frame_bgr, (x, y), 4, (0, 255, 160), -1)
