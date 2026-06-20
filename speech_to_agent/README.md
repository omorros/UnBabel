# speech → agent (OffBabel Speak-leg spike)

A standalone test of the OffBabel **Speak** pipeline, in isolation from the web UI, robot, and
memory — so it can be de-risked on its own (PRD §8, the 11:00 spike) before it's wired into
`offbabel/server.py`.

```
push-to-talk mic  ──►  faster-whisper  ──►  two-step tutor agent (on Exo)  ──►  {reply, correction}
  (sounddevice)         (STT, 16kHz)              │
                                                  ├─ Step 1  Corrector → {wrong, right, note} | null
                                                  └─ Step 2  Tutor     → {reply}  (target language)
```

`{reply, correction}` is exactly the contract `offbabel/web/app.js` already renders (the
transcript bubble + the correction strip), so this drops into the WebSocket handler later with
no UI changes.

## Files

| File | What it does |
|---|---|
| `record.py` | Push-to-talk mic capture → 16kHz mono float32 (`PTTRecorder`) |
| `stt.py` | faster-whisper transcription (lazy, offline-safe, multilingual) |
| `agent.py` | The **two-step agent**: Corrector → Tutor, with robust JSON coercion |
| `loop.py` | Interactive end-to-end loop (mic **or** typed text) |
| `doctor.py` | Preflight: checks LLM, mic, STT, agent — run it offline to prove no phone-home |
| `config.py` | All knobs, env-overridable (mirrors `offbabel/config.py`) |

## Quick start

```bash
pip install -r speech_to_agent/requirements.txt
```

Then run the loop **from the repo root**:

```bash
# Mac demo machine (Exo on :52415):
python -m speech_to_agent.loop

# Windows dev box (Exo can't run here — use Ollama, identical client code):
set OFFBABEL_LLM_URL=http://localhost:11434/v1
set OFFBABEL_LLM_MODEL=qwen3:1.7b
python -m speech_to_agent.loop
```

In the loop: **ENTER** to talk (ENTER again to stop), or **type a sentence** to skip the mic and
test just the agent, `l es|en|cs` to switch language, `q` to quit.

Smaller tests:
```bash
python -m speech_to_agent.doctor                       # full preflight (LLM + mic + STT + agent)
python -m speech_to_agent.record                       # mic only: list devices, record 3s
python -m speech_to_agent.agent es "Yo tiene un perro" # agent only (no mic, no STT)
```

## Engine: Exo (demo) vs Ollama (dev/fallback)

The client is just the `openai` SDK pointed at a `base_url`, so the two are interchangeable —
only `OFFBABEL_LLM_URL` + `OFFBABEL_LLM_MODEL` change.

| | Exo (prize target) | Ollama (dev + fallback) |
|---|---|---|
| base_url | `http://localhost:52415/v1` | `http://localhost:11434/v1` |
| runs on Windows? | **no** | yes |
| model string | HF repo, e.g. `mlx-community/Qwen3-0.6B-4bit` | tag, e.g. `qwen3:1.7b` |
| enforces `response_format`? | **no — silently ignored** | yes (`json_schema`) |

**Verified against the live `exo` source** (not assumed): Exo is OpenAI-compatible at `:52415`,
streams SSE, ignores the api_key (pass any non-empty string), and accepts **arbitrary HF repos**
(`POST /models/add`), not just its built-in registry. Offline via `EXO_OFFLINE=true`.

> ⚠️ **The big gotcha:** Exo accepts `response_format` in the request but **never applies it** —
> there's no server-side JSON enforcement. That's *why* `agent.py` coerces JSON with a hard prompt
> + a parse-and-retry ladder (`json_repair`) instead of trusting the API. On Ollama you additionally
> get real schema enforcement, but the code never depends on it.

## Model choice

- **`mlx-community/Qwen3-0.6B-4bit`** (default) — in Exo's registry, ~327MB, instant. Good enough to
  prove the pipeline, but **too weak for trustworthy Czech grammar + strict JSON**.
- **`mlx-community/Qwen3-4B-Instruct-2507-4bit`** — the quality pick (Apache-2.0, ~2.5GB). Add to Exo:
  ```bash
  curl -X POST http://localhost:52415/models/add -d '{"model_id":"mlx-community/Qwen3-4B-Instruct-2507-4bit"}'
  export OFFBABEL_LLM_MODEL=mlx-community/Qwen3-4B-Instruct-2507-4bit
  ```
- Qwen3 **"thinking" mode is the #1 latency killer** — `agent.py` disables it with `/no_think` in
  the system prompts. Keep that.

## Offline prep (PRD §2A)

1. On venue wifi: run `python -m speech_to_agent.doctor` once — this downloads the Whisper model and
   makes Exo fetch the LLM weights.
2. Then go offline and re-run with the flags set:
   ```bash
   export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1   # Whisper / HF libs
   # start Exo with: EXO_OFFLINE=true HF_HUB_OFFLINE=1 uv run exo
   python -m speech_to_agent.doctor
   ```
   Anything that hangs >1–2s or throws a connection error is a phone-home to fix.

## Wiring into offbabel later

`offbabel/web/app.js` already sends `speak_ptt_start` / `speak_ptt_stop` / `set_language`, but
`offbabel/server.py` only stubs `speak_text`. To integrate:

- `speak_ptt_start` → `recorder.start()` + emit `emote("listening")`
- `speak_ptt_stop`  → `audio = recorder.stop()` → `text = await asyncio.to_thread(transcribe, audio, lang)`
  → send `{"type":"transcript","role":"user","text":text}`
- then `result = await asyncio.to_thread(respond, text, lang)` →
  send the tutor `transcript`, the `correction`, `emote("speaking")`, and (later) Piper TTS + `memory.log_*`

Capture start/stop are non-blocking; only `transcribe`/`respond` go on a worker thread so the
asyncio loop is never stalled.
