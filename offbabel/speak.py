"""Speak mode (Person A / Mac): mic -> faster-whisper -> Exo LLM -> Piper TTS -> speakers.

The tutor is scenario- and level-aware: it steers the learner toward the lesson's target
phrases, weaves in due-for-review items, corrects gently, and emits hidden <hit>/<correction>
tags we parse to drive the spaced-repetition engine (srs.py). transcribe()/speak_tts() are the
parts that still need the cached models on the Mac.

Wire-up in server.py is already done (the speak_text handler calls tutor_turn). On the Mac, fill
in transcribe() + speak_tts() and route push-to-talk audio through them.
"""
import re

from . import config, curriculum

LANG_NAMES = {"es": "Spanish", "en": "English", "cs": "Czech"}


def build_system_prompt(language, scenario, due_items):
    lang = LANG_NAMES.get(language, "Spanish")
    if not scenario:
        return (
            f"You are a friendly {lang} conversation tutor. Reply ONLY in {lang}, "
            f"1-2 short sentences, keep the conversation going, and correct mistakes gently."
        )
    level = scenario.get("level", "A1")
    targets = scenario.get("targets", [])
    role = scenario.get("tutor_role", "a friendly tutor")
    speech = curriculum.LEVEL_SPEECH.get(level, "")
    support = curriculum.LEVEL_SUPPORT.get(level, "")
    review_txt = "; ".join(due_items) if due_items else "none"
    return f"""You are OffBabel's {lang} tutor. Role: {role}. Speak ONLY in {lang}.
Level {level}: {speech} Scaffolding: {support}
GOALS this session - steer the learner to PRODUCE each one naturally (do not list them aloud): {"; ".join(targets)}
REVIEW - work these previously-missed items back in if you can: {review_txt}
Correct gently (recast), at most one correction per turn. Keep your reply to 1-2 short sentences.
After your spoken reply, on new lines output tags:
  <hit>goal</hit>  for each goal the learner just produced correctly (zero or more),
  <correction wrong="..." right="..." note="..."/>  if they made a mistake, else nothing.
Output your spoken reply first, then the tags."""


_HIT = re.compile(r"<hit>(.*?)</hit>", re.S)
_CORR = re.compile(r'<correction\s+wrong="(.*?)"\s+right="(.*?)"(?:\s+note="(.*?)")?\s*/>', re.S)


def parse_tags(raw):
    hits = [h.strip() for h in _HIT.findall(raw) if h.strip()]
    corr = None
    m = _CORR.search(raw)
    if m:
        corr = {"wrong": m.group(1), "right": m.group(2), "note": m.group(3) or ""}
    reply = re.split(r"<hit>|<correction", raw, maxsplit=1)[0].strip()
    return reply or raw.strip(), hits, corr


def get_llm():
    """OpenAI client pointed at Exo (localhost:52415); set OFFBABEL_LLM_URL to use Ollama instead."""
    from openai import OpenAI

    return OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)


def tutor_turn(text, language, scenario=None, due_items=None):
    """One tutor turn. Returns {reply, hits: [...], correction: {...}|None}."""
    client = get_llm()
    sys = build_system_prompt(language, scenario, due_items or [])
    resp = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[{"role": "system", "content": sys}, {"role": "user", "content": text}],
        temperature=0.4,
    )
    raw = resp.choices[0].message.content or ""
    reply, hits, corr = parse_tags(raw)
    return {"reply": reply, "hits": hits, "correction": corr}


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
