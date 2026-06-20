# OffBabel

On-device language tutor, fully offline. Two modes, one app:

- **Speak**: hold a spoken conversation in a target language and get corrected.
- **Sign**: fingerspell BSL to the webcam and get instant "got it / try again."

Everything runs locally. No internet, no cloud. A Reachy Mini robot reacts and celebrates.
Full plan, stress tests, and sponsor strategy live in `Bridge_PRD.md`.

## Machines

- **Mac (demo machine)**: runs everything heavy. Exo (LLM), faster-whisper, Piper, MediaPipe,
  Cognee, the backend, the UI, and the Reachy connection. The demo runs here.
- **Windows (dev box)**: builds the portable Python + web. Used to develop and to record BSL data.

Exo does not run on Windows, so the LLM lives on the Mac at `localhost:52415` (Ollama is the
one-line fallback via `OFFBABEL_LLM_URL`).

## Setup (both machines, on wifi, before going offline)

```
pip install -r offbabel/requirements.txt
```

Then cache models per `Bridge_PRD.md` section 11 (Exo model, Whisper small, Piper voices,
MediaPipe, Reachy emotions library, Ollama + Cognee). After caching set
`HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`.

## Run

```
# the app (serves UI + WebSocket, all localhost)
python -m offbabel.server
# open http://127.0.0.1:8500   (Chrome --kiosk for the demo)
```

### Sign mode (the 13:00 gate)
```
python -m offbabel.sign.capture   # record ~30-50 samples per letter, both hands, venue light
python -m offbabel.sign.train     # holdout accuracy + the E/O vowel-trap report
python -m offbabel.sign.live      # standalone live test
```
In the app, entering Sign mode starts the live webcam stream automatically.

### Speak mode (Mac)
Fill in the TODOs in `offbabel/speak.py` (faster-whisper + Piper local paths), then wire
`tutor_turn()` into the server's `speak_text` handler as documented in that file.

### Memory
SQLite is the source of truth (`offbabel/memory.py`), always on. Cognee is the additive sponsor
layer (`offbabel/cognee_memory.py`); configure it offline per the header in that file.

## Layout

```
offbabel/
  server.py          backend: serves UI + WebSocket hub + emote contract
  config.py          ports, model ids, paths, offline flags (all env-overridable)
  memory.py          SQLite struggle store + needs-review list
  cognee_memory.py   Cognee graph layer (sponsor bonus, offline-configured)
  speak.py           Speak loop scaffold (Mac): Whisper -> Exo -> Piper
  robot.py           Reachy wrapper, best-effort (no-op if robot absent)
  sign/
    landmarks.py     normalize MediaPipe hands -> 126-d feature vector
    capture.py       record labeled landmark samples
    train.py         KNN train + holdout + vowel-trap check
    live.py          standalone live detection
    engine.py        background webcam stream -> WebSocket detections
  web/               vanilla HTML/JS/CSS UI (no CDN, offline-safe)
```
