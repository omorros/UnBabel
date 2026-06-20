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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from . import config, curriculum, srs
from .sign.engine import SignEngine

# Prefer the built React UI; fall back to the vanilla shell during early dev.
# abspath matters: StaticFiles' security check fails to serve files if the dir contains "..".
_DIST = os.path.abspath(os.path.join(config.BASE, "..", "offbabel-ui", "dist"))
WEB_DIR = _DIST if os.path.isdir(_DIST) else os.path.abspath(os.path.join(config.BASE, "web"))

app = FastAPI()
srs.init()
sign_engine = SignEngine()

# best-effort robot: a missing or offline robot must never crash the demo
try:
    from .robot import emote as _robot_emote
except Exception:  # noqa: BLE001
    _robot_emote = None

# per-session lesson state (single local user)
session = {"scenario": None, "level": "L3", "hits": []}


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
        await emote("idle")
        await hub.send({"type": "mode", "mode": mode})
        if mode == "speak":
            session["scenario"] = msg.get("scenario")
            session["level"] = msg.get("level")
            session["hits"] = []
            sign_engine.stop()
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
        await _handle_speak(msg)

    elif t == "sign_demo_letter":
        letter = msg.get("label", "")
        lvl = session.get("level") or "L3"
        if letter:
            srs.record_result("sign", lvl, lvl, letter, True)
        await hub.send({"type": "sign_detect", "label": letter, "confidence": 1.0, "stable": True})
        await hub.send({"type": "summary", "summary": srs.summary()})

    elif t == "celebrate":
        await emote("happy")


async def _handle_speak(msg):
    await tutor_exchange(
        msg.get("text", ""),
        msg.get("language", "es"),
        msg.get("scenario") or session.get("scenario"),
    )


async def _tts(text, lang):
    """Best-effort speech output. No-op until speak_tts (Piper) is wired on the Mac."""
    if not text:
        return
    try:
        from . import speak
        await asyncio.to_thread(speak.speak_tts, text, lang)
    except NotImplementedError:
        pass
    except Exception as e:  # noqa: BLE001
        print("tts failed (ignored):", e)


async def tutor_exchange(text, lang, scn_id):
    """One tutor turn -> transcript + correction + audio + SRS + summary.

    Reusable seam: the push-to-talk path (once Whisper is wired on the Mac) transcribes the
    mic audio to `text` and calls THIS function, so speech and text inputs share one path.
    """
    scn = curriculum.scenario(scn_id) if scn_id else None

    await emote("listening")
    await hub.send({"type": "transcript", "role": "user", "text": text})
    await emote("speaking")

    data = None
    try:
        from . import speak
        due = [i["prompt"] for i in srs.due_items(mode="speak", limit=3)]
        data = await asyncio.to_thread(speak.tutor_turn, text, lang, scn, due)
    except Exception as e:  # noqa: BLE001
        print("tutor LLM unavailable, stub:", e)

    if not data:
        # stub so the lesson still demos without an LLM: advance one target
        nxt = None
        if scn:
            remaining = [tg for tg in scn["targets"] if tg not in session["hits"]]
            nxt = remaining[0] if remaining else None
        data = {"reply": "(tutor offline) " + text, "hits": [nxt] if nxt else [], "correction": None}

    if scn:
        for h in data.get("hits", []):
            if h and h not in session["hits"]:
                session["hits"].append(h)
                srs.record_result("speak", scn["id"], scn["level"], h, True)
        corr = data.get("correction")
        if corr and corr.get("wrong"):
            srs.record_result("speak", scn["id"], scn["level"], corr["wrong"][:40], False)

    reply = data.get("reply", "")
    await hub.send({"type": "transcript", "role": "tutor", "text": reply})
    if data.get("correction"):
        await hub.send({"type": "correction", **data["correction"]})
    if scn:
        await hub.send({"type": "targets", "count": len(session["hits"])})
    await emote("idle")
    await hub.send({"type": "summary", "summary": srs.summary()})
    asyncio.create_task(_tts(reply, lang))  # play audio concurrently (no-op until Piper is wired)


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
