"""OffBabel backend: serves the web UI and a WebSocket the UI talks to.

Run:  python -m offbabel.server      (or: uvicorn offbabel.server:app --port 8500)
Open: http://127.0.0.1:8500          (Chrome --kiosk for the demo)

Everything here is localhost or the local LAN. Nothing touches the internet. The browser is
just a local screen. Speak and Sign engines push events through the same hub() as they land.
"""
import asyncio
import json
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, memory

WEB_DIR = os.path.join(config.BASE, "web")

app = FastAPI()
memory.init()

# best-effort robot: a missing or offline robot must never crash the demo
try:
    from .robot import emote as _robot_emote
except Exception:  # noqa: BLE001
    _robot_emote = None


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


@app.get("/")
async def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await hub.connect(ws)
    await ws.send_text(json.dumps(
        {"type": "status", "offline": True, "stats": memory.stats()}
    ))
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            await handle(msg)
    except WebSocketDisconnect:
        hub.disconnect(ws)


async def handle(msg):
    """Route a UI message. Stubs below keep the UI fully click-testable before the engines land."""
    t = msg.get("type")

    if t == "set_mode":
        await emote("idle")
        await hub.send({"type": "mode", "mode": msg.get("mode")})

    elif t == "get_progress":
        await hub.send({"type": "progress", "stats": memory.stats(),
                        "review": memory.needs_review()})

    elif t == "speak_text":
        # STUB until the Speak leg lands: echo the user, fake a tutor reply + correction.
        text = msg.get("text", "")
        lang = msg.get("language", "es")
        await emote("listening")
        await hub.send({"type": "transcript", "role": "user", "text": text})
        await asyncio.sleep(0.3)
        await emote("speaking")
        await hub.send({"type": "transcript", "role": "tutor",
                        "text": "(reply will come from Exo)"})
        await hub.send({"type": "correction", "wrong": text, "right": text,
                        "note": "(corrections will come from the tutor LLM)"})
        memory.log_seen("word", lang, text[:40] or "phrase")

    elif t == "sign_demo_letter":
        # STUB: click-test the spelling UI before the classifier is wired.
        letter = msg.get("label", "")
        await hub.send({"type": "sign_detect", "label": letter,
                        "confidence": 1.0, "stable": True})

    elif t == "celebrate":
        await emote("happy")


def main():
    import uvicorn
    print(f"OffBabel on http://{config.HOST}:{config.PORT}  (offline; open in Chrome)")
    uvicorn.run(app, host=config.HOST, port=config.PORT)


if __name__ == "__main__":
    main()
