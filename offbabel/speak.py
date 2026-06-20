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
    client = get_llm()
    sys = build_system_prompt(language, scenario, due_items or [])
    messages = [{"role": "system", "content": sys}] + history
    resp = client.chat.completions.create(
        model=config.LLM_MODEL, messages=messages, temperature=0.5
    )
    raw = resp.choices[0].message.content or ""
    data = _extract_json(raw) or {"reply": raw.strip()}
    data.setdefault("reply", "")
    data.setdefault("translation", "")
    data.setdefault("correction", None)
    data.setdefault("hits", [])
    return data


def transcribe(audio, language):
    """TODO (Mac): faster-whisper 'small' int8, load once at startup.

    from faster_whisper import WhisperModel
    _MODEL = WhisperModel(config.WHISPER_SIZE, device="cpu", compute_type="int8")
    segments, _ = _MODEL.transcribe(audio, language=language)
    return " ".join(s.text for s in segments).strip()
    """
    raise NotImplementedError("wire faster-whisper on the Mac")


def speak_tts(text, language):
    """TODO (Mac): Piper with the LOCAL voice path for `language` (never a bare name).

    voice = config.PIPER_VOICES[language]
    subprocess: piper -m {voice} -f out.wav  then play out.wav on the speakers.
    """
    raise NotImplementedError("wire Piper on the Mac with local voice paths")
