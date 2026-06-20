"""End-to-end spike: speech -> agent, in a terminal. Proves the whole Speak leg with no web,
no robot, no memory attached (PRD section 8, "get one full corrected exchange working").

Run (Mac, Exo):              python -m speech_to_agent.loop
Run (Windows dev, Ollama):   set OFFBABEL_LLM_URL=http://localhost:11434/v1 && set OFFBABEL_LLM_MODEL=qwen3:1.7b && python -m speech_to_agent.loop

Controls:
  ENTER                start recording; ENTER again to stop -> transcribe -> tutor agent
  <type text> ENTER    skip the mic, send that text straight to the agent (no-mic testing)
  l es | l en          switch language
  r                    toggle speaking through Reachy (robot) on/off
  q                    quit
"""
from . import config
from .agent import respond

# This spike speaks through Reachy Mini, which has one TTS voice per language (see reachy_speaker.py),
# so the Speak loop is scoped to the two showcase languages for now.
SPEAK_LANGS = ("en", "es")

_lang = config.DEFAULT_LANG if config.DEFAULT_LANG in SPEAK_LANGS else "es"
_recorder = None
_speak = True  # speak replies through the robot; toggle with "r" (e.g. when no tunnel is up)


def _banner():
    print("=" * 64)
    print(f"  speech -> agent spike   lang={_lang} ({config.LANG_NAMES.get(_lang, _lang)})")
    print(f"  llm  : {config.LLM_BASE_URL}")
    print(f"  model: {config.LLM_MODEL}")
    print(f"  robot: {'on (speaking replies)' if _speak else 'off'}")
    print("  ENTER = talk   |   type text = send text   |   l es|en   |   r = robot   |   q = quit")
    print("=" * 64)


def _listen():
    """Record from the mic between two ENTER presses, then transcribe."""
    global _recorder
    from .record import PTTRecorder
    from .stt import transcribe
    if _recorder is None:
        _recorder = PTTRecorder()
    _recorder.start()
    input("  recording... [ENTER to stop] ")
    audio = _recorder.stop()
    print("  transcribing...")
    return transcribe(audio, _lang)


def _show(result):
    print(f"\n  tutor> {result['reply']}")
    corr = result.get("correction")
    if corr:
        print(f"  fix  > you said \"{corr['wrong']}\"  ->  try \"{corr['right']}\"")
        if corr.get("note"):
            print(f"         ({corr['note']})")
    else:
        print("  ✓  no mistakes")


def _speak_reply(text):
    """Speak the tutor's reply through Reachy. Fails soft: a missing tunnel/robot must never
    break the conversation loop (PRD: robot = enhancement, not dependency)."""
    if not _speak or not text:
        return
    from .reachy_speaker import say_reachy  # lazy: no robot deps unless we actually speak
    try:
        say_reachy(text, language=_lang)
    except Exception as e:  # noqa: BLE001
        print(f"  (robot offline — showing text only: {e})")


def _think_and_respond(text):
    """Run the agent while Reachy does its gentle 'thinking' idle motion — turning the latency
    gap into character. Motion stops (and returns to neutral) before the reply is spoken."""
    print("\n  Reachy is thinking…")
    motion = None
    if _speak:  # only move the robot when robot output is enabled (toggle with 'r')
        from .reachy_motion import thinking as motion
        motion.start()
    try:
        return respond(text, _lang)
    finally:
        if motion:
            motion.stop()


def main():
    global _lang, _speak
    _banner()
    while True:
        try:
            cmd = input(f"\n[{_lang}] ENTER to talk, or type text> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return

        if cmd == "q":
            print("bye")
            return
        if cmd == "r":
            _speak = not _speak
            print(f"  -> robot speech: {'on' if _speak else 'off'}")
            continue
        if cmd.startswith("l "):
            code = cmd[2:].strip()
            if code in SPEAK_LANGS:
                _lang = code
                print(f"  -> language: {config.LANG_NAMES[_lang]}")
            else:
                print("  use: l es | l en")
            continue

        if cmd == "":  # mic mode
            try:
                text = _listen()
            except Exception as e:  # noqa: BLE001
                print(f"  mic/STT error: {e}")
                continue
            if not text:
                print("  (heard nothing — hold the mic, speak, then press ENTER)")
                continue
            print(f"  heard> {text}")
        else:          # text mode
            text = cmd

        try:
            result = _think_and_respond(text)
        except Exception as e:  # noqa: BLE001
            print(f"  agent error: {e}")
            continue
        _show(result)
        _speak_reply(result["reply"])


if __name__ == "__main__":
    main()
