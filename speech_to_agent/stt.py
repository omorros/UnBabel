"""Speech-to-text with faster-whisper. Lazy-loaded, multilingual, offline-safe.

Engine choice: faster-whisper runs on the Windows dev box AND the Mac (CPU int8; it has no
Metal backend, but 'small' on a short push-to-talk clip is ~1-2s, which is fine). On the Mac
you can later swap in mlx-whisper for GPU speed; keeping faster-whisper means one codepath
everywhere. Whisper input MUST be 16kHz mono float32 — record.py guarantees that.

OFFLINE: after caching the model on venue wifi, export HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1
so the HF libs never attempt a network call (PRD section 2A). faster-whisper auto-downloads the
model on first use, so trigger that download while you still have wifi.
"""
from . import config

_model = None


def _load():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel  # imported lazily so text-only testing needs no STT
        device = config.WHISPER_DEVICE
        if device == "auto":
            device = "cpu"  # faster-whisper/CTranslate2 has no Apple-GPU backend; CPU is portable
        print(f"[stt] loading faster-whisper '{config.WHISPER_SIZE}' "
              f"({device}/{config.WHISPER_COMPUTE}) ...")
        _model = WhisperModel(config.WHISPER_SIZE, device=device, compute_type=config.WHISPER_COMPUTE)
    return _model


def transcribe(audio, language=None):
    """audio: float32 mono 16kHz np.ndarray. language: 'es'|'en'|'cs' — pass it explicitly;
    autodetect misfires on a learner's imperfect speech. Returns the transcript string."""
    if audio is None or len(audio) == 0:
        return ""
    model = _load()
    segments, _info = model.transcribe(
        audio,
        language=language or config.DEFAULT_LANG,
        vad_filter=True,   # trim the silence around a push-to-talk clip
        beam_size=1,       # greedy = fastest; plenty for short utterances
    )
    return " ".join(seg.text for seg in segments).strip()


def warm_up():
    """Pre-load the model (e.g. at server start) so the first real utterance isn't slow."""
    _load()
