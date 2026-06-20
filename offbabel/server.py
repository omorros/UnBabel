"""OffBabel backend: serves the web UI and a WebSocket the UI talks to.

Run:  python -m offbabel.server      (or: uvicorn offbabel.server:app --port 8500)
Open: http://127.0.0.1:8500          (Chrome --kiosk for the demo)

Serves the built shadcn UI from offbabel-ui/dist when present, else the vanilla web/ shell.
Everything here is localhost or the local LAN. Nothing touches the internet. The learning
loop is driven by srs.py (spaced repetition); the tutor + sign engine feed results into it.
"""
import asyncio
import json
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, StreamingResponse

from . import config, curriculum, speak, srs
from .listen import SpeakListener
from .sign.engine import SignEngine

# Prefer the built React UI; fall back to the vanilla shell during early dev.
# abspath matters: StaticFiles' security check fails to serve files if the dir contains "..".
_DIST = os.path.abspath(os.path.join(config.BASE, "..", "offbabel-ui", "dist"))
WEB_DIR = _DIST if os.path.isdir(_DIST) else os.path.abspath(os.path.join(config.BASE, "web"))

app = FastAPI()
srs.init()
sign_engine = SignEngine()
listener = SpeakListener()

# best-effort robot: a missing or offline robot must never crash the demo
try:
    from .robot import emote as _robot_emote
except Exception:  # noqa: BLE001
    _robot_emote = None

# per-session lesson state (single local user)
session = {"scenario": None, "level": "L3", "lang": "es", "hits": [], "history": [], "turn": 0}


class Hub:
    """Tracks connected UI clients and broadcasts JSON events to all of them."""

    def __init__(self):
        self.clients = set()

    async def connect(self, ws):
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws):
        self.clients.discard(ws)

    async def send(self, msg):
        for ws in list(self.clients):
            try:
                await ws.send_text(json.dumps(msg))
            except Exception:  # noqa: BLE001
                self.clients.discard(ws)


hub = Hub()


async def emote(emotion):
    """Shared emote contract: drive the on-screen avatar AND (best-effort) the robot."""
    await hub.send({"type": "emote", "emotion": emotion})
    if _robot_emote:
        try:
            _robot_emote(emotion)
        except Exception as e:  # noqa: BLE001
            print("robot emote failed (ignored):", e)


def _review_for_ui():
    out = []
    for it in srs.needs_review():
        out.append({
            "type": "sign" if it["mode"] == "sign" else "word",
            "language": "bsl" if it["mode"] == "sign" else "es",
            "value": it["prompt"],
            "miss_count": it["miss_count"],
        })
    return out


@app.on_event("startup")
async def _maybe_connect_robot():
    """On the Mac, run with OFFBABEL_ROBOT=1 to connect Reachy over the LAN at startup."""
    if os.environ.get("OFFBABEL_ROBOT"):
        try:
            from . import robot
            await asyncio.to_thread(robot.connect)
        except Exception as e:  # noqa: BLE001
            print("robot connect skipped:", e)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await hub.connect(ws)
    await ws.send_text(json.dumps({"type": "status", "offline": True, "summary": srs.summary()}))
    try:
        while True:
            await handle(json.loads(await ws.receive_text()))
    except WebSocketDisconnect:
        hub.disconnect(ws)


async def handle(msg):
    t = msg.get("type")

    if t == "set_mode":
        mode = msg.get("mode")
        listener.stop()  # stop any mic listener on a mode change
        await emote("idle")
        await hub.send({"type": "mode", "mode": mode})
        if mode == "speak":
            session.update(
                scenario=msg.get("scenario"),
                level=msg.get("level"),
                lang=msg.get("language", session.get("lang", "es")),
                hits=[], history=[], turn=0,
            )
            sign_engine.stop()
            session["history"].append({"role": "user", "content": speak.OPENING_DIRECTIVE})
            await _run_tutor()  # Reachy opens the conversation
        elif mode == "sign":
            session["level"] = msg.get("level") or "L3"
            sign_engine.start(asyncio.get_running_loop(), hub.send, session["level"])
        else:
            sign_engine.stop()

    elif t in ("sign_start", "sign_stop"):
        if t == "sign_start":
            sign_engine.start(asyncio.get_running_loop(), hub.send, session.get("level") or "L3")
        else:
            sign_engine.stop()

    elif t == "get_progress":
        await hub.send({"type": "progress", "summary": srs.summary(), "review": _review_for_ui()})

    elif t == "speak_text":
        await emote("listening")
        await hub.send({"type": "transcript", "role": "user", "text": msg.get("text", "")})
        session["lang"] = msg.get("language", session.get("lang", "es"))
        session["history"].append({"role": "user", "content": msg.get("text", "")})
        session["turn"] = session.get("turn", 0) + 1
        await _run_tutor()

    elif t == "speak_help":
        await emote("listening")
        await hub.send({"type": "transcript", "role": "user", "text": "(I don't understand)"})
        session["history"].append({"role": "user", "content": speak.HELP_DIRECTIVE})
        await _run_tutor(help_turn=True)

    elif t == "conversation_start":
        loop = asyncio.get_running_loop()
        from speech_to_agent.reachy_motion import thinking
        # pre-load Whisper so the FIRST utterance isn't slow (model load up front, not mid-turn)
        asyncio.create_task(asyncio.to_thread(speak.warm_whisper))
        listener.start(
            lambda text: asyncio.run_coroutine_threadsafe(_voice_turn(text), loop),
            session.get("lang", "es"),
            on_speech_end=thinking.start,  # 'thinking' motion the moment you stop talking (covers STT+LLM)
        )
        await emote("listening")

    elif t == "conversation_stop":
        listener.stop()
        from speech_to_agent.reachy_motion import thinking
        await asyncio.to_thread(thinking.stop)  # clean up any in-flight 'thinking' motion on pause
        await emote("idle")

    elif t == "sign_demo_letter":
        letter = msg.get("label", "")
        lvl = session.get("level") or "L3"
        if letter:
            srs.record_result("sign", lvl, lvl, letter, True)
        await hub.send({"type": "sign_detect", "label": letter, "confidence": 1.0, "stable": True})
        await hub.send({"type": "summary", "summary": srs.summary()})

    elif t == "celebrate":
        await emote("happy")


async def _voice_turn(text):
    """A transcribed mic utterance -> the same path as a typed message."""
    if not text or not text.strip():
        # speech ended but nothing transcribed -> stop the 'thinking' motion started on_speech_end
        from speech_to_agent.reachy_motion import thinking
        await asyncio.to_thread(thinking.stop)
        return
    await hub.send({"type": "transcript", "role": "user", "text": text})
    session["history"].append({"role": "user", "content": text})
    session["turn"] = session.get("turn", 0) + 1
    await _run_tutor()


async def _tts(text, lang):
    """Speak the tutor's reply aloud through Reachy (macOS say -> ffmpeg -> daemon, with wobble).
    Best-effort: a missing tunnel/robot must never break the session."""
    if not text:
        return
    try:
        from speech_to_agent.reachy_speaker import say_reachy
        await asyncio.to_thread(say_reachy, text, language=lang)
    except Exception as e:  # noqa: BLE001
        print("tts failed (ignored):", e)


# Scripted fallback so the whole conversation demos even with no LLM (and as a safety net).
# Mirrors the greetings lesson: open -> a couple of turns (with one correction) -> wrap.
_STUB = {
    "es": {
        "open": {"reply": "¡Hola! Soy Reachy. ¿Cómo te llamas?",
                 "translation": "Hi! I'm Reachy. What's your name?"},
        "help": {"reply": "Claro. ¿Có... mo... te... lla... mas?",
                 "translation": "Sure. What is your name?"},
        "turns": [
            {"reply": "¡Encantado! ¿De dónde eres?",
             "translation": "Nice to meet you! Where are you from?"},
            {"reply": "¡Genial! ¿Y qué te gusta hacer en tu tiempo libre?",
             "translation": "Great! And what do you like to do in your free time?"},
            {"reply": "¡Muy bien hablado! Por hoy, ¡buen trabajo!",
             "translation": "Very well said! That's it for today, great job!"},
        ],
    },
    "en": {
        "open": {"reply": "Hi! I'm Reachy. What's your name?",
                 "translation": "Hi! I'm Reachy. What's your name?"},
        "help": {"reply": "Sure. What... is... your... name?",
                 "translation": "Sure. What is your name?"},
        "turns": [
            {"reply": "Nice to meet you! Where are you from?",
             "translation": "Nice to meet you! Where are you from?"},
            {"reply": "Great! And what do you like to do in your free time?",
             "translation": "Great! And what do you like to do in your free time?"},
            {"reply": "Really well said. That's it for today, great job!",
             "translation": "Really well said. That's it for today, great job!"},
        ],
    },
}


def _stub_reply(lang, scn, help_turn):
    s = _STUB.get(lang, _STUB["en"])
    if help_turn:
        d = s["help"]
        return {"reply": d["reply"], "translation": d["translation"], "correction": None, "hits": []}
    turn = session.get("turn", 0)
    d = s["open"] if turn <= 0 else s["turns"][min(turn - 1, len(s["turns"]) - 1)]
    hits = []
    if scn and turn > 0:
        remaining = [t for t in scn["targets"] if t not in session["hits"]]
        if remaining:
            hits = [remaining[0]]
    # the offline stub never fabricates corrections (it can't analyze input); real corrections
    # only come from the live LLM (Exo on the Mac / Ollama).
    return {"reply": d["reply"], "translation": d.get("translation", ""),
            "correction": None, "hits": hits}


async def _run_tutor(help_turn=False):
    """Generate + send one tutor turn. session['history'] already holds the latest user turn.

    Real path uses the LLM with full conversation history (coherent multi-turn). If no LLM is
    reachable it falls back to the scripted _stub_reply so the demo still flows.
    """
    lang = session.get("lang", "es")
    scn = curriculum.scenario(session.get("scenario")) if session.get("scenario") else None

    await emote("speaking")
    # Reachy does its gentle 'thinking' idle motion while the LLM generates, then returns its head
    # to level before speaking. The single-owner motion lock keeps it from fighting the TTS wobble.
    from speech_to_agent.reachy_motion import thinking
    thinking.start()
    data = None
    try:
        due = [i["prompt"] for i in srs.due_items(mode="speak", limit=3)]
        data = await asyncio.to_thread(speak.tutor_turn, session["history"], lang, scn, due)
    except Exception as e:  # noqa: BLE001
        print("tutor LLM unavailable, stub:", e)
    finally:
        await asyncio.to_thread(thinking.stop)  # stop + return head to level, off the event loop
    if not data or not data.get("reply"):
        data = _stub_reply(lang, scn, help_turn)

    session["history"].append({"role": "assistant", "content": data.get("reply", "")})

    if scn and not help_turn:
        for h in data.get("hits", []):
            if h and h not in session["hits"]:
                session["hits"].append(h)
                srs.record_result("speak", scn["id"], scn["level"], h, True)
        corr = data.get("correction")
        if corr and corr.get("wrong"):
            srs.record_result("speak", scn["id"], scn["level"], corr["wrong"][:40], False)

    reply = data.get("reply", "")
    await hub.send({"type": "transcript", "role": "tutor", "text": reply,
                    "translation": data.get("translation", "")})
    if data.get("correction"):
        await hub.send({"type": "correction", **data["correction"]})
    if scn:
        await hub.send({"type": "targets", "count": len(session["hits"])})
    await emote("idle")
    await hub.send({"type": "summary", "summary": srs.summary()})
    asyncio.create_task(_tts(reply, lang))  # plays concurrently (no-op until Piper is wired)


# ---- Reachy Mini live camera (consumed by the Sign screen's <img>) ----
# Defined BEFORE the catch-all spa() route below, which would otherwise swallow these paths.

@app.get("/reachy-media/video.mjpeg")
async def reachy_video(request: Request):
    """Stream the robot camera as multipart MJPEG. A plain <img src> renders it directly."""
    from .reachy_video import streamer
    streamer.add_client()

    async def frames():
        last = None
        try:
            while True:
                if await request.is_disconnected():
                    break
                frame = streamer.get_latest_frame()
                if frame is not None and frame is not last:
                    last = frame
                    yield (b"--frame\r\nContent-Type: image/jpeg\r\n"
                           + f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii")
                           + frame + b"\r\n")
                await asyncio.sleep(0.03)  # ~30fps ceiling; we send only new frames
        finally:
            streamer.remove_client()  # last viewer leaving stops the shared SSH stream

    return StreamingResponse(
        frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"},
    )


@app.get("/reachy-media/video/status")
async def reachy_video_status():
    from .reachy_video import streamer
    return streamer.status()


# Serve the static UI with a catch-all (robust on Windows): return the file if it exists
# (index.html, /assets/*, /mascot.png), else fall back to index.html for the single-page app.
@app.get("/{path:path}")
async def spa(path: str):
    candidate = os.path.normpath(os.path.join(WEB_DIR, path))
    if candidate.startswith(WEB_DIR) and os.path.isfile(candidate):
        return FileResponse(candidate)
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


def main():
    import uvicorn
    print(f"OffBabel on http://{config.HOST}:{config.PORT}  serving {os.path.basename(WEB_DIR)}/  (offline)")
    uvicorn.run(app, host=config.HOST, port=config.PORT)


if __name__ == "__main__":
    main()
