"""The tutor "agent" — a small THREE-STEP agent pipeline. This is the heart of "feed to the agents".

  Step 1  Corrector : utterance        -> {"correction": {wrong, right, note} | null}   (target lang)
  Step 2  Tutor     : utterance + corr -> {"reply": "..."}                               (target lang)
  Step 3  Verify    : reply             -> {"verified": "<corrected>" | null}            (target lang)

Merged result:  {"reply": str, "correction": {wrong,right,note} | None}
— exactly the contract offbabel's UI already renders (transcript bubble + correction strip).

WHY THREE STEPS (not one mega-call): a 0.6-4B model told to simultaneously judge grammar in three
languages, write a natural reply, AND emit strict JSON drifts on all three. One job per call keeps
each honest, isolates failures, and gives an "Agent hackathon" a legible plan->act flow.
Step 3 ensures the tutor's reply is grammatically correct — it serves as a spoken model for the learner.

WHY NOT response_format: Exo accepts the field but SILENTLY IGNORES it (verified against exo
source) — there is no server-side JSON enforcement. So we coerce JSON with a hard prompt + a robust
parse ladder + one retry. (Point LLM_BASE_URL at Ollama and you additionally get real json_schema
enforcement for free — a bonus, not a dependency.)
"""
import json
import re

from openai import OpenAI

from . import config

_client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)

# /no_think = Qwen3's soft switch to skip the <think> block (engine-agnostic; the #1 latency lever).
CORRECTOR_SYS = """You are a careful {lang} grammar checker for a language learner who is SPEAKING, not writing. /no_think
The input is a transcript of ONE short spoken utterance in {lang} from a beginner (A2-B1 level).
Important rules:
- The speaker may use natural speech patterns: fillers ("um", "uh", "like"), false starts, self-corrections, or simplified sentences. These are NORMAL for speech — do NOT flag them as errors.
- ONLY correct genuine grammar mistakes (wrong verb conjugations, incorrect articles, wrong prepositions, word order errors, gender agreement errors, etc.).
- ONLY correct genuine word-choice mistakes where the wrong word was chosen (e.g., confusing two similar words).
- If you are unsure whether the input is a speech disfluency or a real error, give the speaker the benefit of the doubt and do NOT flag it.
- If the transcript contains an apparent error that might be a speech recognition mistake, do NOT flag it unless the grammar is clearly wrong.
Return ONLY a JSON object — no prose, no markdown — of exactly this shape:
{{"correction": {{"wrong": "<the user's exact words>", "right": "<the corrected words>", "note": "<short reason, in {lang}>"}}}}
If the utterance is already correct (or only contains normal speech patterns), return EXACTLY: {{"correction": null}}
Only fix real grammar or word-choice mistakes. Never invent an error."""

TUTOR_SYS = """You are a warm, patient {lang} conversation partner for a beginner (level A2-B1). /no_think
Reply ONLY in {lang}, in 1-2 short sentences, and end with one simple question to keep the chat going.
Use simple vocabulary. Do NOT mention grammar, corrections, or that you are an AI.
Your response must be grammatically PERFECT in {lang} — you are a model for the learner to imitate.
Return ONLY a JSON object: {{"reply": "<your reply, in {lang}>"}}"""

VERIFY_SYS = """You are a strict {lang} grammar checker for a language tutor. /no_think
The input is a tutor's reply that will be spoken aloud to a beginner learner (A2-B1 level).
Check the reply for ANY grammar mistakes, word-choice errors, gender agreement errors, article misuse, incorrect prepositions, or any other errors in {lang}.
Return ONLY a JSON object: {{"verified": "<corrected reply if any errors, or null if perfect>"}}
If the reply is already grammatically perfect and natural in {lang}, return EXACTLY: {{"verified": null}}"""


def respond(utterance, language=None):
    """Run the three-step agent. Returns {"reply": str, "correction": {...}|None}."""
    if not utterance or not utterance.strip():
        return {"reply": "", "correction": None}
    lang_code = language or config.DEFAULT_LANG
    lang = config.LANG_NAMES.get(lang_code, lang_code)

    correction = _correct(utterance, lang)        # step 1
    reply = _reply(utterance, lang, correction)   # step 2
    verified = _verify(reply, lang)               # step 3
    if verified:
        reply = verified
    return {"reply": reply, "correction": correction}


def _verify(reply, lang):
    """Step 3: verify tutor's reply is grammatically perfect. Returns corrected string or None."""
    raw = _chat(VERIFY_SYS.format(lang=lang), reply, config.LLM_TEMP_CORRECTOR)
    data = _parse_json(raw) or {}
    verified = data.get("verified")
    if verified and isinstance(verified, str) and verified.strip():
        return verified.strip()
    return None  # null or no correction needed -> keep original reply


def _correct(utterance, lang):
    raw = _chat(CORRECTOR_SYS.format(lang=lang), utterance, config.LLM_TEMP_CORRECTOR)
    data = _parse_json(raw) or {}
    corr = data.get("correction")
    if isinstance(corr, dict) and corr.get("wrong") and corr.get("right"):
        return {"wrong": corr["wrong"], "right": corr["right"], "note": corr.get("note", "")}
    return None  # null, malformed, or "no mistake" -> no correction strip


def _reply(utterance, lang, correction):
    user = utterance
    if correction:
        # context-only nudge; the tutor must NOT read the correction back to the learner
        user += (f'\n(Context, do not mention: the learner said "{correction["wrong"]}", '
                 f'better is "{correction["right"]}".)')
    raw = _chat(TUTOR_SYS.format(lang=lang), user, config.LLM_TEMP_TUTOR)
    data = _parse_json(raw)
    if data and isinstance(data.get("reply"), str) and data["reply"].strip():
        return data["reply"].strip()
    # the model wrote prose instead of JSON -> salvage the prose (minus any think block)
    return _strip_think(raw).strip() or "..."


def _chat(system, user, temperature, _retry=True):
    # reasoning_effort="none" turns off the model's <think> phase (Exo honors it). Without this a
    # reasoning model spends the whole token budget thinking and returns empty content.
    extra = {}
    if config.LLM_REASONING_EFFORT:
        extra["extra_body"] = {"reasoning_effort": config.LLM_REASONING_EFFORT}
    try:
        resp = _client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=config.LLM_MAX_TOKENS,
            **extra,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:  # noqa: BLE001
        if _retry:
            return _chat(system, user, temperature, _retry=False)  # one bounded retry
        raise RuntimeError(
            f"LLM call failed against {config.LLM_BASE_URL} (model={config.LLM_MODEL}): {e}\n"
            f"Is Exo/Ollama running? Try OFFBABEL_LLM_URL={config.OLLAMA_BASE_URL} to use Ollama.")


# ---- robust JSON coercion (Exo won't enforce it for us) -----------------------------------
def _strip_think(text):
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL)


def _strip_fences(text):
    return re.sub(r"```(?:json)?|```", "", text or "").strip()


def _first_object(text):
    """Return the first balanced {...} block (brace-matching, not a naive regex)."""
    if not text:
        return None
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return text[start:]  # truncated -> let json_repair try the tail


def _parse_json(text):
    """Ladder: raw -> de-fenced -> first balanced object; each tried with json then json_repair."""
    text = _strip_think(text)
    for candidate in (text, _strip_fences(text), _first_object(_strip_fences(text))):
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except Exception:  # noqa: BLE001
            try:
                import json_repair  # optional dependency; salvages near-miss JSON
                return json_repair.loads(candidate)
            except Exception:  # noqa: BLE001
                continue
    return None


if __name__ == "__main__":
    # quick text-only smoke test of the agent (no mic needed)
    import sys
    lang = sys.argv[1] if len(sys.argv) > 1 else config.DEFAULT_LANG
    text = " ".join(sys.argv[2:]) or "Yo tiene un perro"
    print(f"in  [{lang}]: {text}")
    print("out:", json.dumps(respond(text, lang), ensure_ascii=False, indent=2))
