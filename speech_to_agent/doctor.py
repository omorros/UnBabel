"""Preflight for the speech->agent spike. Run it on venue wifi to cache + verify, then run it
again with wifi physically OFF to prove nothing phones home (PRD section 2A acceptance test).

Checks, in order:
  1. LLM endpoint reachable -> lists downloaded models -> one round-trip + latency
  2. mic captures non-zero audio (catches the macOS "records all zeros" permission trap)
  3. faster-whisper loads and transcribes the captured clip
  4. full agent on the transcript (or a canned sentence)

Run:  python -m speech_to_agent.doctor
"""
import time

from . import config

OK, BAD = "  [ok]", "  [!!]"


def _timed(fn):
    t0 = time.perf_counter()
    out = fn()
    return out, time.perf_counter() - t0


def check_llm():
    print(f"\n1) LLM @ {config.LLM_BASE_URL}  (model={config.LLM_MODEL})")
    from openai import OpenAI
    client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)
    try:
        models = [m.id for m in client.models.list().data]
        print(f"{OK} reachable. {len(models)} model(s): {', '.join(models[:6]) or '(none)'}")
        if config.LLM_MODEL not in models:
            print(f"{BAD} '{config.LLM_MODEL}' not in the list — Exo will download it on first call "
                  f"(needs wifi), or add/pull it first.")
    except Exception as e:  # noqa: BLE001
        print(f"{BAD} cannot reach endpoint: {e}")
        print("       Is Exo (:52415) or Ollama (:11434) running? "
              f"Try OFFBABEL_LLM_URL={config.OLLAMA_BASE_URL}")
        return False
    try:
        (resp, dt) = _timed(lambda: client.chat.completions.create(
            model=config.LLM_MODEL, max_tokens=16, temperature=0,
            messages=[{"role": "user", "content": "Reply with the single word: ok"}]))
        print(f"{OK} chat round-trip {dt:.2f}s -> {resp.choices[0].message.content!r}")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"{BAD} chat call failed: {e}")
        return False


def check_mic_and_stt():
    print("\n2) mic capture (recording 2s — speak now)")
    import numpy as np
    from .record import PTTRecorder
    try:
        rec = PTTRecorder()
        rec.start()
        time.sleep(2.0)
        audio = rec.stop()
    except Exception as e:  # noqa: BLE001
        print(f"{BAD} {e}")
        return None
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    print(f"{OK} {audio.size} samples @ {config.TARGET_SR}Hz  peak={peak:.3f}")

    print("\n3) faster-whisper transcription")
    try:
        from .stt import transcribe
        (text, dt) = _timed(lambda: transcribe(audio, config.DEFAULT_LANG))
        print(f"{OK} {dt:.2f}s -> {text!r}")
        return text
    except Exception as e:  # noqa: BLE001
        print(f"{BAD} {e}")
        return None


def check_agent(text):
    sample = text or "Yo tiene un perro"
    print(f"\n4) tutor agent on: {sample!r}")
    try:
        from .agent import respond
        (result, dt) = _timed(lambda: respond(sample, config.DEFAULT_LANG))
        print(f"{OK} {dt:.2f}s")
        print(f"     reply     : {result['reply']!r}")
        print(f"     correction: {result['correction']}")
    except Exception as e:  # noqa: BLE001
        print(f"{BAD} {e}")


def main():
    print("=" * 64)
    print("  speech -> agent  PREFLIGHT")
    print("=" * 64)
    llm_ok = check_llm()
    text = check_mic_and_stt()
    if llm_ok:
        check_agent(text)
    else:
        print("\n(skipping the agent check — LLM endpoint is down)")
    print("\nDone. To prove offline: kill wifi, set HF_HUB_OFFLINE=1 + EXO_OFFLINE=true, re-run.")


if __name__ == "__main__":
    main()
