"""Config for the speech->agent spike. Env-overridable (mirrors offbabel/config.py) so this
ports straight into offbabel/ once proven. Everything is localhost / on-device — no internet.

Engine: default is Exo on the Mac demo machine (:52415, the prize target). Exo CANNOT run on the
Windows dev box, so develop there against Ollama:
    set OFFBABEL_LLM_URL=http://localhost:11434/v1
    set OFFBABEL_LLM_MODEL=qwen3:1.7b        (or qwen3:4b — multilingual incl. Czech)
The client code is identical either way; only these two env vars change.
"""
import os

# ---- LLM (the "agent") --------------------------------------------------------------------
EXO_BASE_URL = "http://localhost:52415/v1"      # Exo default (verified: exo docs/api.md)
OLLAMA_BASE_URL = "http://localhost:11434/v1"   # one-line fallback; also runs on Windows
LLM_BASE_URL = os.environ.get("OFFBABEL_LLM_URL", EXO_BASE_URL)

# Exo wants a HuggingFace repo string; Ollama wants a tag (e.g. "qwen3:1.7b").
# Default = the Gemma 4 E2B model loaded in the demo Exo. Good for Spanish/English conversation;
# Czech is weaker (have a native speaker verify). For a tinier option use mlx-community/Qwen3-0.6B-4bit.
LLM_MODEL = os.environ.get("OFFBABEL_LLM_MODEL", "mlx-community/gemma-4-e2b-it-4bit")
LLM_API_KEY = os.environ.get("OFFBABEL_LLM_KEY", "offbabel")  # ignored by Exo/Ollama; must be non-empty

# Exo SILENTLY IGNORES response_format (verified against exo source) — no server-side JSON
# enforcement — so we coerce JSON via the prompt + a robust parse ladder + one retry (see agent.py).
LLM_TEMP_CORRECTOR = float(os.environ.get("OFFBABEL_TEMP_CORR", "0.2"))  # low: grammar judgement
LLM_TEMP_TUTOR = float(os.environ.get("OFFBABEL_TEMP_TUTOR", "0.6"))     # warmer: natural reply
LLM_MAX_TOKENS = int(os.environ.get("OFFBABEL_MAX_TOKENS", "160"))

# Gemma 4 / Qwen3 "think" before answering, which burns the token budget (empty content) and adds
# latency. Exo honors reasoning_effort="none" to turn it off (verified). Set OFFBABEL_REASONING=""
# to omit the field entirely for a server/model that rejects it.
LLM_REASONING_EFFORT = os.environ.get("OFFBABEL_REASONING", "none")

# ---- STT (faster-whisper: runs on BOTH the Windows dev box and the Mac) --------------------
WHISPER_SIZE = os.environ.get("OFFBABEL_WHISPER", "small")
WHISPER_DEVICE = os.environ.get("OFFBABEL_WHISPER_DEVICE", "auto")    # auto|cpu|cuda
WHISPER_COMPUTE = os.environ.get("OFFBABEL_WHISPER_COMPUTE", "int8")  # int8 = fast on CPU

# ---- Audio capture ------------------------------------------------------------------------
TARGET_SR = 16000                              # Whisper expects 16kHz mono float32
# OFFBABEL_MIC: leave unset for the system default input, or set a device index ("1") or name.
_mic = os.environ.get("OFFBABEL_MIC")
MIC_DEVICE = int(_mic) if (_mic and _mic.isdigit()) else _mic

# ---- Reachy robot daemon (HTTP) -----------------------------------------------------------
# Reach it via an SSH tunnel:  ssh -N -L 8000:127.0.0.1:8000 pollen@reachy-mini.local
REACHY_API_BASE = os.environ.get("OFFBABEL_REACHY_API", "http://localhost:8000")

# ---- Languages (Spanish showcase, English, Czech bonus — PRD section 3) --------------------
DEFAULT_LANG = os.environ.get("OFFBABEL_LANG", "es")
LANG_NAMES = {"es": "Spanish", "en": "English", "cs": "Czech"}
