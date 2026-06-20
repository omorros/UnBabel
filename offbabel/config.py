"""Shared config. Everything overridable by env var so we never hardcode a guess.

Offline note: on the Mac demo machine, export EXO_OFFLINE=1 HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1 after caching (see PRD 2A).
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
MODELS_DIR = os.path.join(BASE, "models")
LANDMARKS_CSV = os.path.join(DATA_DIR, "landmarks.csv")
SIGN_MODEL_PATH = os.path.join(DATA_DIR, "sign_knn.joblib")
# Vendored MediaPipe Tasks hand model (committed to the repo -> offline + identical on every machine)
HAND_MODEL_PATH = os.environ.get(
    "OFFBABEL_HAND_MODEL", os.path.join(MODELS_DIR, "hand_landmarker.task")
)

# ---- Sign / vision ----
CAMERA_INDEX = int(os.environ.get("OFFBABEL_CAMERA", "0"))
DEBOUNCE_FRAMES = int(os.environ.get("OFFBABEL_DEBOUNCE", "12"))  # frames of agreement before we accept a letter (higher = steadier)
CONF_THRESHOLD = float(os.environ.get("OFFBABEL_CONF", "0.55"))   # min predict_proba to count a frame
NEG_LABEL = "_"  # "nothing / junk" class — helps reject noise

# ---- Reachy Mini live camera (Sign screen) ----
# The robot has no RTSP server, so we run rpicam-vid on the robot over SSH (MJPEG to stdout) and
# reparse it into a browser MJPEG endpoint. REACHY_SSH_HOST may be an ~/.ssh/config alias or
# "user@host". Default resolution is 640x360 (light over SSH, ample for the Sign panel); bump to
# 1280x720 via env if the LAN can spare the bandwidth.
REACHY_SSH_HOST = os.environ.get("OFFBABEL_REACHY_SSH", "pollen@reachy-mini.local")
REACHY_CAM_WIDTH = int(os.environ.get("OFFBABEL_REACHY_CAM_W", "640"))
REACHY_CAM_HEIGHT = int(os.environ.get("OFFBABEL_REACHY_CAM_H", "360"))
REACHY_CAM_FPS = int(os.environ.get("OFFBABEL_REACHY_CAM_FPS", "30"))

# ---- LLM (Speak) ----
# Exo on the Mac at :52415 is the demo engine; Ollama is the one-line fallback (also used by Cognee).
EXO_BASE_URL = "http://localhost:52415/v1"
OLLAMA_BASE_URL = "http://localhost:11434/v1"
LLM_BASE_URL = os.environ.get("OFFBABEL_LLM_URL", EXO_BASE_URL)
LLM_MODEL = os.environ.get("OFFBABEL_LLM_MODEL", "mlx-community/Qwen3-0.6B-4bit")
LLM_API_KEY = os.environ.get("OFFBABEL_LLM_KEY", "offbabel")  # ignored by Exo/Ollama; must be non-empty

# ---- STT / TTS ----
WHISPER_SIZE = os.environ.get("OFFBABEL_WHISPER", "small")
PIPER_VOICES = {  # fill with local .onnx paths after caching (NEVER a bare name -> would auto-download)
    "es": os.environ.get("OFFBABEL_PIPER_ES", ""),
    "en": os.environ.get("OFFBABEL_PIPER_EN", ""),
    "cs": os.environ.get("OFFBABEL_PIPER_CS", ""),
}

# ---- Server ----
HOST = os.environ.get("OFFBABEL_HOST", "127.0.0.1")
PORT = int(os.environ.get("OFFBABEL_PORT", "8500"))

# ---- Memory ----
MEMORY_DB = os.path.join(DATA_DIR, "memory.sqlite")
