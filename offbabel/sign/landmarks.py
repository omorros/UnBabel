"""Feature engineering: MediaPipe hand landmarks -> normalized, scale/translation-invariant vector.

BSL fingerspelling is TWO-HANDED, so we build a 126-d vector = two 63-d hand slots
(Right then Left, a stable order regardless of detection order). Each hand is:
  1. translated so the wrist sits at the origin,
  2. scaled by the wrist->middle-MCP distance (hand size), so distance from camera doesn't matter.
A missing hand is zero-padded. This trains on geometry, not pixels -> tiny, fast, robust.
"""
import numpy as np

NUM_LANDMARKS = 21
DIMS_PER_HAND = NUM_LANDMARKS * 3   # 63
FEATURE_DIM = DIMS_PER_HAND * 2     # 126  (Right slot, Left slot)

WRIST = 0
MIDDLE_MCP = 9


def normalize_one_hand(landmarks):
    """landmarks: iterable of 21 (x, y, z). Returns a flat (63,) float32 vector."""
    pts = np.asarray(landmarks, dtype=np.float32).reshape(NUM_LANDMARKS, 3)
    pts = pts - pts[WRIST]                      # wrist -> origin
    scale = float(np.linalg.norm(pts[MIDDLE_MCP]))
    if scale < 1e-6:
        scale = 1.0
    pts = pts / scale
    return pts.flatten()


def build_feature_vector(hands):
    """hands: list of (handedness_label, landmarks) where label is 'Left'/'Right'.

    Returns a (126,) vector: Right hand in slot 0, Left in slot 1, zero-padded if absent.
    Ordering by handedness (not detection order) keeps the vector stable across frames.
    """
    right = np.zeros(DIMS_PER_HAND, dtype=np.float32)
    left = np.zeros(DIMS_PER_HAND, dtype=np.float32)
    for label, lm in hands:
        vec = normalize_one_hand(lm)
        if label == "Right":
            right = vec
        else:
            left = vec
    return np.concatenate([right, left])
