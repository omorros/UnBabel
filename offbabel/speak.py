"""Speak mode (Person A / Mac): mic -> faster-whisper -> Exo LLM -> Piper TTS -> speakers.

The tutor (Reachy) holds a multi-turn conversation: it greets and asks the first question,
keeps the dialogue going one question at a time, corrects gently, gives an English translation
of every line (so non-speakers and judges can follow), and can re-explain when the learner does
not understand. It returns structured JSON the server parses to drive captions + the SRS.

transcribe()/speak_tts() are the parts that still need the cached models on the Mac.
"""
import json
import re

from . import config, curriculum

LANG_NAMES = {"es": "Spanish", "en": "English", "cs": "Czech"}

# Injected as user-role turns; the model answers in the target language.
OPENING_DIRECTIVE = "Begin the lesson: greet me warmly by name as Reachy and ask your first simple question."
HELP_DIRECTIVE = "I do not understand. Re-ask your previous question more simply and slowly."


def build_system_prompt(language, scenario, due_items):
    L = LANG_NAMES.get(language, "Spanish")
    if scenario:
        level = scenario.get("level", "A2")
        targets = "; ".join(scenario.get("targets", []))
        speech = curriculum.LEVEL_SPEECH.get(level, "")
    else:
        level, targets, speech = "A2", "everyday conversation", ""
    review = "; ".join(due_items) if due_items else "none"
    return f"""You are Reachy, a warm, encouraging {L} conversation tutor speaking out loud to a learner.
Rules:
- Speak ONLY in {L}. Each turn is 1-2 SHORT sentences and ENDS WITH A QUESTION to keep the conversation going.
- {speech}
- Guide the learner toward practicing these goals, without listing them aloud: {targets}.
- Reuse these previously-missed items if it is natural: {review}.
- If the learner makes a {L} mistake, correct it gently with a recast.
- If the learner says they do not understand, re-ask your PREVIOUS question more simply and slowly.
Return ONLY a JSON object and nothing else:
{{"reply": "<your {L} reply>", "translation": "<plain English translation of your reply>",
  "correction": {{"wrong": "...", "right": "...", "note": "..."}} or null,
  "hits": ["<goal the learner just achieved>", ...]}}"""


def _extract_json(raw):
    m = re.search(r"\{.*\}", raw, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:  # noqa: BLE001
            return None
    return None


def get_llm():
    """OpenAI client pointed at Exo (localhost:52415); set OFFBABEL_LLM_URL to use Ollama instead.

    Short connect timeout -> fails fast to the stub when no LLM is up; generous total timeout so
    a real (slower, local) generation is not cut off.
    """
    import httpx
    from openai import OpenAI

    return OpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        max_retries=0,
        timeout=httpx.Timeout(30.0, connect=0.6),
    )


def tutor_turn(history, language, scenario=None, due_items=None):
    """history: list of {role, content} including the latest user/directive turn.
    Returns {reply, translation, correction|None, hits: [...]}.
    """
    from speech_to_agent.agent import _parse_json  # reuse the proven robust JSON ladder (strips <think>/fences)

    client = get_llm()
    sys = build_system_prompt(language, scenario, due_items or [])
    messages = [{"role": "system", "content": sys}] + history
    kwargs = dict(model=config.LLM_MODEL, messages=messages, temperature=0.3)
    # reasoning_effort="none" stops Gemma/Qwen3 from "thinking" first (which eats the token budget
    # and returns empty content). Exo honors it; harmless on servers that ignore it.
    if config.LLM_REASONING_EFFORT:
        kwargs["extra_body"] = {"reasoning_effort": config.LLM_REASONING_EFFORT}
    try:
        # force valid JSON (Ollama + most OpenAI-compatible servers honor this); Exo ignores it, so
        # we also parse robustly below.
        resp = client.chat.completions.create(response_format={"type": "json_object"}, **kwargs)
    except Exception:  # noqa: BLE001
        resp = client.chat.completions.create(**kwargs)
    raw = resp.choices[0].message.content or ""
    data = _parse_json(raw)
    if not isinstance(data, dict):
        data = {"reply": (raw or "").strip()}
    data.setdefault("reply", "")
    data.setdefault("translation", "")
    data.setdefault("correction", None)
    data.setdefault("hits", [])

    # Reliability: the single-call tutor often misses a grammar mistake while juggling
    # reply+translation+hits. If it returned no correction, double-check the learner's last REAL
    # utterance with speech_to_agent's dedicated corrector (proven, with the wrong==right guard).
    # Skip directives (the opening/help prompts are not learner speech).
    if not data.get("correction"):
        last_user = next((m["content"] for m in reversed(history) if m.get("role") == "user"), "")
        if last_user and last_user not in (OPENING_DIRECTIVE, HELP_DIRECTIVE):
            try:
                from speech_to_agent.agent import _correct
                c = _correct(last_user, LANG_NAMES.get(language, "Spanish"))
                if c:
                    data["correction"] = c
            except Exception:  # noqa: BLE001
                pass
    return data


_WHISPER = None


def _get_whisper():
    global _WHISPER
    if _WHISPER is None:
        from faster_whisper import WhisperModel
        _WHISPER = WhisperModel(config.WHISPER_SIZE, device="cpu", compute_type="int8")
    return _WHISPER


def warm_whisper():
    """Pre-load the Whisper model so the FIRST conversation utterance isn't slow (the model load
    happens up front when the mic starts, not mid-turn)."""
    _get_whisper()


def transcribe(audio, language):
    """audio: float32 mono numpy array at 16 kHz. Returns the recognized text."""
    model = _get_whisper()
    segments, _ = model.transcribe(audio, language=language, vad_filter=True)
    return " ".join(s.text for s in segments).strip()


def speak_tts(text, language):
    """TODO (Mac): Piper with the LOCAL voice path for `language` (never a bare name).

    voice = config.PIPER_VOICES[language]
    subprocess: piper -m {voice} -f out.wav  then play out.wav on the speakers.
    """
    raise NotImplementedError("wire Piper on the Mac with local voice paths")
