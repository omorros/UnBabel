# OffBabel integration guide (for the Mac / Speak + robot)

How the app fits together and exactly where your pieces plug in. Everything is local; the
browser is just a screen that talks to the Python backend over a WebSocket.

## How it works

```
Browser UI (offbabel-ui)  ──ws──►  server.py (FastAPI)
                                      ├─ tutor_exchange()  ── speak.py ── Exo LLM (:52415)
                                      │        └─ speak.transcribe / speak.speak_tts  (mic / speakers)
                                      ├─ SignEngine ── MediaPipe + KNN ── webcam
                                      ├─ srs.py  (Leitner spaced repetition, SQLite)  ← the learning loop
                                      ├─ robot.py  ── Reachy over LAN  (emotes)
                                      └─ cognee_memory.py  (graph insight, optional)
```

- The **learning loop is already wired**: every Speak target and Sign letter records into `srs.py`,
  and the UI gets live `summary` (streak / due / mastery). You do not need to touch this.
- `server.tutor_exchange(text, lang, scenario_id)` is the single shared path for a tutor turn.
  Text input already calls it. Wire push-to-talk to call it too (see below).

## WebSocket contract (already implemented in server.py)

Client → server: `set_mode {mode, scenario?, level?}`, `speak_text {text, language, scenario}`,
`speak_ptt_start` / `speak_ptt_stop`, `sign_demo_letter {label}`, `get_progress`, `celebrate`.

Server → client: `status {summary}`, `transcript {role, text}`, `correction {wrong,right,note}`,
`emote {emotion}`, `sign_detect {label, confidence, stable}`, `targets {count}`,
`summary {streak,dueToday,masterySpeak,masterySign}`, `progress {summary, review}`, `mode {mode}`.

## Your wiring points (each is a small fill-in)

### 1. Exo LLM (Speak tutor) — already wired, just run it
`speak.tutor_turn` calls an OpenAI-compatible endpoint at `config.LLM_BASE_URL` (default
`http://localhost:52415/v1`, model `mlx-community/Qwen3-0.6B-4bit`). Start Exo and it works.
Fallback to Ollama with no code change: `OFFBABEL_LLM_URL=http://localhost:11434/v1 OFFBABEL_LLM_MODEL=llama3.1:8b`.
Confirm the port + model string with the Exo reps.

### 2. Whisper (mic → text) — fill `speak.transcribe`
Implement `speak.transcribe(audio, language)` (faster-whisper small int8, load once). Then make
push-to-talk capture audio: in `server.handle`, on `speak_ptt_start` start a `sounddevice`
recording, on `speak_ptt_stop` stop it, transcribe, and call `await tutor_exchange(text, lang, session["scenario"])`.
Text input already shares that path, so once transcribe + capture work, speech "just works".

### 3. Piper (text → speech) — fill `speak.speak_tts`
Implement `speak.speak_tts(text, language)` with the LOCAL voice path from `config.PIPER_VOICES`
(never a bare voice name). It is **already auto-called** after each tutor reply (`server._tts`),
so once you fill it, the tutor speaks. No server change needed.

### 4. Robot (Reachy) — fill `robot.py`, run with a flag
Fill `robot.connect()` (it already releases the camera/mic via `media_backend="no_media"`) and the
real move names in `EMOTION_TO_MOVE`. Start the server with `OFFBABEL_ROBOT=1` and it connects at
startup; `emote(...)` is already called at the right moments (listening / speaking / happy).

### 5. Cognee (graph insight) — optional sponsor layer
Configure offline per the header in `cognee_memory.py` (Ollama LLM + fastembed embeddings,
`STRUCTURED_OUTPUT_FRAMEWORK=BAML`). It reads the same `srs` items. Test:
`python -m offbabel.cognee_memory`. SQLite/`srs` is the source of truth; Cognee is additive.

## Run / deploy

```bash
# 1. build the UI once (on wifi); the server serves it
cd offbabel-ui && npm run build && cd ..
# 2. run the app (Mac demo machine)
OFFBABEL_ROBOT=1 python -m offbabel.server
#    open http://127.0.0.1:8500  (Chrome --kiosk for the demo)
# 3. verify readiness any time
python -m offbabel.doctor
```
After caching models, go offline: set `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 EXO_OFFLINE=1`.
