# UnBabel — Build-Ready PRD

> An on-device tutor led by a **Reachy Mini (Wireless)** robot. **Speak** mode: hold a spoken conversation in a target language and get corrected. **Sign** mode: fingerspell **BSL** to the laptop webcam and get instant "got it / try again." Everything runs **locally** — no internet, no cloud. One product, two communities.

**Event:** Localhost — On-Device Agent Hackathon · Dawn Capital, London · Sat 20 Jun 2026 (09:00–20:00)
**The hard rule:** everything runs locally during the demo. No internet, no cloud calls — this is **pass/fail** for the event (see §2A).
**The bet (say it out loud):** sign recognition is the differentiator and the risk; **Speak is the safety net.** We prove sign in the first 90 minutes and decide at the 13:00 gate.
**⚠️ Name note:** "UnBabel" collides with **Unbabel** — an established Lisbon AI-translation company (YC '14, Microsoft/Salesforce-backed, tagline *"break down language barriers"*), squarely in this domain. The AI-engineer judges will likely recognise it, so it may read as derivative. Fine for a one-day hack, but consider an offline-forward twist that's yours: **OffBabel**, **Babel Offline**, or **Babel Mini** (ties to Reachy Mini). Decide on the day.

---

## 0. Locked decisions

| Decision | Choice | Consequence for the build |
|---|---|---|
| **Robot unit** | Reachy Mini **Wireless** | Daemon runs **on the robot** (auto-starts on power-on). The **brain runs on the laptop**. Robot + laptop must share a **no-internet LAN**. Vision/audio run on the laptop, not the Pi. |
| **Team** | **2 builders** | **Person A → Speak** end-to-end. **Person B → Sign** end-to-end. Converge on shell + memory after the gate. |
| **Languages** | **English + Spanish + Czech** (third locked to Czech) | Pipeline is language-agnostic. Czech over Vietnamese because **Czech is non-tonal** → cleaner Whisper transcripts and tractable grammar correction; Vietnamese's 6 tones live in diacritics that STT drops, making the "correct the learner" loop fragile. Adding Czech = one Piper voice (`cs_CZ-jirka`) + a dropdown entry. Your teammate speaks it, so he verifies live. |
| **Sign language** | **BSL** (British, two-handed) | London = BSL, **not ASL**. Use BSL reference data. MediaPipe must track **2 hands**. |
| **Robot role in Sign** | **Watches & reacts only** | Reachy has no hands. The human signs; Reachy celebrates/encourages. **Never pitch "robot signs."** |
| **Vision source** | **Laptop webcam** (not the robot camera) | De-risks the gamble: no robot-camera-over-wifi latency. Robot releases its camera via `media_backend="no_media"`. |
| **Audio I/O for Speak** | **Laptop mic + speakers** (default); robot mic/speaker = stretch | Keeps latency-sensitive audio off wifi. Robot is pure expression over the control link. |

---

## 1. Scope

**MVP — must demo (offline):**
- Mode-select home screen + persistent **"On-device · No internet"** badge.
- **Speak:** one target language (Spanish first — best voices), push-to-talk, live transcript, **at least one visible correction**, Reachy speaks + emotes.
- **Sign:** BSL fingerspelling for **5–8 visually-distinct letters**, live laptop-webcam recognition, spell **one short word** (H-E-L-L-O), Reachy celebrates on completion.
- A simple **Progress** view backed by local memory.

**Nice-to-have (only if ahead):**
- 2nd/3rd language live, larger sign vocabulary, "needs review" resurfacing, polished avatar animation, robot mic/camera path, Captur/Overmind integration.

**Cut first if behind:**
- Drop to **one mode, done cleanly.** Sign is the differentiator; Speak is the safety net. **If sign won't converge, ship Speak-only and ship it polished.**

**Gate rule (13:00):** If a tiny classifier reliably distinguishes ≥5 BSL letters on the laptop webcam under venue lighting → **full dual-mode.** If it's still fighting you → **Speak-only pivot**, Person B moves to harden Speak + shell + memory. Decide at lunch, no later.

---

## 2. Architecture (Wireless-specific)

```
        ┌──────────────────────── LAPTOP — "the brain" ─────────────────────────┐
        │                                                                        │
 Laptop mic ─PTT─▶ faster-whisper ─▶ Exo LLM (localhost) ─▶ Piper TTS ─▶ speakers│  (SPEAK)
        │                 │                  │                                   │
 Laptop webcam ─▶ MediaPipe Hands ─▶ landmark classifier ─▶ feedback             │  (SIGN)
        │                 │                  │                                   │
        │                 └────▶ Cognee (struggled items, progress) ◀────────────┤  (MEMORY)
        │                                    │                                   │
        │   Web UI (Speak / Sign / Progress) ◀── WebSocket ──▶ Python backend    │
        │                                    │                                   │
        │            Reachy SDK / FastAPI  ──── LAN (no internet) ───────────────┼─▶ ROBOT (Pi)
        └────────────────────────────────────────────────────────────────────────┘   • daemon (auto-on)
                                                                                       • motors / antennas / body
        NO INTERNET — everything above is local                                        • (camera/mic released)
```

**The two-box split (do not violate):**
- **Robot (Raspberry Pi):** runs **only the daemon** (auto-starts when powered on; exposes a FastAPI REST + WebSocket API at the robot's `:8000`, plus the Python SDK over the LAN). Verify by opening `http://<robot-ip>:8000/docs` — you should see the Reachy SDK API.
- **Laptop:** runs **everything heavy** — Whisper, Exo, Piper, MediaPipe, the classifier, Cognee, the backend, and the web UI.

**Connecting (Wireless):**
- `from reachy_mini import ReachyMini` → `ReachyMini()` **auto-detects** and connects over the **network** for Wireless. Force it if needed: `ReachyMini(connection_mode="network")`.
- **Release the robot's camera/mic so you can use the laptop's:** `ReachyMini(media_backend="no_media")`. This tells the daemon to release camera + audio hardware so OpenCV/sounddevice on the laptop own them. The robot still takes motor commands.
- *(Stretch, if you want the robot's own camera/mic later: leave `media_backend="default"` → it auto-uses WebRTC when remote, streaming H.264 video + Opus audio from robot to laptop. Don't build the demo on this; it's a wifi-dependent nicety.)*

**The no-internet LAN — pick ONE and test it before noon:**
1. **Laptop joins the robot's own broadcast network.** Reachy Wireless broadcasts a hotspot on first boot. Laptop on that network → robot reachable → no internet by construction. (Trade-off: laptop can't also be on venue wifi — so **download everything first**, then switch.)
2. **Dedicated travel router / switch with no WAN.** Robot + laptop both join it. Cleanest, most demo-proof. "Pull the ethernet" = unplug the router's WAN (or there never was one).

> ⚠️ **The Wireless-specific demo killer:** models cached but **robot unreachable when the network drops.** On Lite you'd pull a USB-irrelevant ethernet; on Wireless the robot link *is* the network. Lock option 1 or 2 and rehearse the exact offline state you'll demo in.

---

## 2A. ⚠️ Offline hardening — the phone-home audit (READ THIS)

Fully offline is **pass/fail** for this event. The trap isn't "we forgot to run something locally" — it's that several libraries you've *cached* still try a network call at runtime (to validate the cache or auto-download a default) and, with no internet, that call **hangs or throws** instead of failing gracefully. **"Cached" ≠ "offline-safe."** Audit every component, then prove it with the network physically off.

| Component | Phones home? | Why | Fix |
|---|---|---|---|
| faster-whisper (HF libs) | **Yes** | First-run model download + a metadata/etag check on every load | Pre-download the model; set `HF_HUB_OFFLINE=1` + `TRANSFORMERS_OFFLINE=1` so the libs don't even attempt a network call |
| Exo + its model | **Yes** | Downloads model weights from HF on first run; may check for updates | Run a test inference on venue wifi; confirm it answers with internet **off**; respects the HF offline env vars |
| **Reachy emotions library** | **Yes — easy to miss** | `RecordedMoves("pollen-robotics/reachy-mini-emotions-library")` is a **HuggingFace repo ID** — instantiating it fetches from HF | Instantiate it once online to cache; then `HF_HUB_OFFLINE=1`. Test `play_move` with internet off |
| MediaPipe Hands | **Yes** (first use) | Downloads the hand-landmark `.task`/tflite bundle on first run | Run it once online to cache, or ship the model file locally and point to it |
| Cognee | **Yes — by default** | Defaults to **OpenAI** for LLM + embeddings; may also pull a default embedder from HF | Configure a **local provider (Ollama)** + local embedding model; cache both; test `add → cognify → search` offline. SQLite fallback ready |
| Ollama models | First `pull` only | Model download | `ollama pull` on venue wifi; serves at `localhost:11434` offline thereafter |
| Piper | Only if you let it | Auto-downloads a voice if you reference one by **name** at runtime | Download `.onnx` + `.json` explicitly; pass **local file paths**, never a bare name |
| **Frontend assets** | **Yes — the silent killer** | Any CDN link fails offline: Tailwind CDN, Google Fonts, React/icons from unpkg/cdnjs | **Vendor everything locally** — no CDN `<script>`/`<link>`, self-host fonts, bundle JS/CSS |
| Laptop wifi (behaviour) | **Risk** | Laptop may silently re-join remembered **venue wifi**, dropping the robot hotspot *and* putting you back online | **Forget/deprioritise venue wifi** for the demo, or use the travel router; consider airplane-mode + only the local link |
| scikit-learn classifier | No | Trained locally on your own data | — |
| `pip install` | Obviously | Needs the package index | Install **everything before** going offline; optional `pip download` wheelhouse as backup |

### The acceptance test (the one that actually matters)
By **16:30**, physically kill internet (and set the HF offline flags), then run the **entire demo end-to-end** — Speak exchange, Sign spelling, Progress, robot reactions. **Anything that hangs >1–2s or throws a connection error is a phone-home you missed.** Fix it now, not at 18:30. Then run it **twice** — once on the robot's hotspot, once on the travel router — so both network setups are proven.

> The judges' bar is "show it working with no connectivity." **Your bar should be: we've already run the whole thing with the wifi physically off, and nothing reached out.**

---

## 3. Speak pipeline — **Person A**

**Recommended approach: a lean custom loop, not a fork.** The official `reachy_mini_conversation_app` gives you mic handling + a layered motion system for free, but its realtime path defaults to a Hugging Face WebSocket server (`HF_REALTIME_WS_URL`, default `localhost:8765`) and re-pointing it at your own local STT/LLM/TTS means matching its realtime protocol under time pressure. **Build your own loop** — full control, no protocol reverse-engineering — and pull just the **emotions library** + `goto_target` from the SDK for expression. Keep the conversation app open as a *reference* for VAD and motion ideas.

**Flow:**
```
push-to-talk (laptop mic, sounddevice)
   → faster-whisper "small" int8  (language=es/en/cs)
   → Exo LLM (localhost, OpenAI-compatible)   ← tutor system prompt
   → parse reply + correction
   → Piper TTS (target-language voice) → laptop speakers
   → robot emote (play_move) on each reply; "listening" pose while mic is held
   → stream transcript + correction strip to UI over WebSocket
   → log any correction to Cognee
```

**Why push-to-talk (not always-on):** the room is loud. Hold-to-talk + an optional text input fallback. This is also a stress-test mitigation — don't fight VAD in a hackathon hall.

**Per-language config:**

| Language | Whisper | Piper voice | LLM competence (small model) | Who verifies |
|---|---|---|---|---|
| **Spanish** | `language="es"` | `es_ES` (or `es_MX`/`es_AR`), medium/high | Strong | You |
| **English** | `language="en"` | `en_US` / `en_GB`, medium | Strongest | Both |
| **Czech** ✅ *(locked third)* | `language="cs"` | `cs_CZ-jirka`, medium (single voice) | Weaker than ES/EN — keep corrections to grammar/word-choice, not pronunciation | Teammate |
| ~~Vietnamese~~ *(rejected)* | — | — | **Tonal** — Whisper drops the diacritics that carry tone, so the correct-the-learner loop misfires. Cut for reliability. | — |

> **Why Czech wins the "fewer issues" test:** it's non-tonal, so the Whisper → correct → Piper loop stays honest, and a native speaker (your teammate) is on the mic to vouch for the corrections. Spanish is still the **showcase** language; Czech is the "we support more, live-verified" proof point. Lead with Spanish, show Czech if time allows.

**Tutor system prompt (starting point):**
> "You are a friendly, patient {LANGUAGE} conversation tutor. Reply **only in {LANGUAGE}**, 1–2 short sentences, and keep the conversation going with a simple question. If the learner's last message has a grammar or word-choice mistake, briefly correct it. Return JSON: `{\"reply\": \"...\", \"correction\": {\"wrong\": \"...\", \"right\": \"...\", \"note\": \"...\"} | null}`. Keep vocabulary simple (A2–B1)."

Parse the JSON → speak `reply` via Piper → if `correction` is non-null, render the **correction strip** (`you said X → try Y`) and log it to Cognee.

**Setup (laptop):**
```bash
pip install faster-whisper sounddevice numpy openai piper-tts
# faster-whisper auto-downloads the model on first use — DO IT ON VENUE WIFI:
python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"

# Piper voices (download .onnx + .onnx.json per language) from HuggingFace rhasspy/piper-voices:
#   es_ES-*   en_US-*   cs_CZ-jirka-*   (Czech is the locked third)
# Test:  echo "hola, ¿cómo estás?" | piper -m es_ES-xxx.onnx -f out.wav

# Exo (track partner) serves an OpenAI-compatible endpoint at localhost.
# Start it, cache a small multilingual model (Qwen3-class), and GRAB THE PORT FROM ITS STARTUP LOG.
```
```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:<EXO_PORT>/v1", api_key="not-needed")  # confirm port from Exo log
```
> Exo's default port shows in its startup log — read it there, don't hardcode a guess. The Exo reps are on-site; confirm the model string and endpoint with them early.

---

## 4. Sign pipeline — **Person B** (the gamble — de-risk in the first 90 min)

**Flow:**
```
laptop webcam (OpenCV)
   → MediaPipe Hands (max_num_hands=2)  → 21 landmarks × up to 2 hands
   → normalize (translate to wrist, scale by hand size) → feature vector
   → classifier (KNN baseline → MLP if time) → predicted letter + confidence
   → debounce (require N consistent frames) → "Detected: A ✓" / "Hold steady…"
   → spell-a-word: advance letter on confident match; progress bar fills
   → robot celebrate (play_move "happy") on completed word
   → log misses to Cognee
```

**BSL is two-handed.** Set `max_num_hands=2`. Use **BSL fingerspelling reference data**, not ASL. Start with letters that are **visually distinct** and avoid confusable pairs early; expand only after the core set is solid.

**Data collection protocol (the thing that makes or breaks it):**
1. Record yourselves, **under the actual venue lighting**, against a plain background.
2. **30–50 samples per letter**, both hands in frame, slight natural variation (angle, distance).
3. Capture the **normalized landmark vectors**, not raw images — you're training on geometry, so it's tiny and fast.
4. Hold out a few samples per letter to sanity-check accuracy. Target: clean separation on the held-out set before you trust it live.

**Feature engineering (do this — raw pixel coords won't generalize):**
- Translate all landmarks so the wrist = origin.
- Scale by a stable reference distance (e.g. wrist→middle-finger-MCP) so it's distance-invariant.
- Concatenate both hands' normalized vectors (pad if only one hand detected).

**Classifier:** start with **scikit-learn KNN** (zero training time, instant iteration). If you have headroom after the gate, swap to a **tiny MLP** for smoother confidence. KNN is the de-risk; MLP is the polish.

**Start tiny — suggested first set:** pick 5–8 letters whose BSL handshapes look least alike, then add the letters you need to spell your demo word. Spelling **H-E-L-L-O** needs **H, E, L, O** — make sure those four are rock-solid.

**Setup (laptop):**
```bash
pip install mediapipe opencv-python scikit-learn numpy
# verify hand tracking on the laptop camera FIRST (before any ML):
#   open webcam → draw 2-hand landmarks → confirm stable tracking under venue light
```

---

## 5. Memory — Cognee (shared)

**Purpose:** store struggled words/signs → drive the "needs review" list and adaptive resurfacing.

**Minimal schema (conceptual):** per item — `type` (word|sign), `language`, `value`, `miss_count`, `last_seen`. Query: "items with highest miss_count not seen recently" → the review list.

```bash
pip install cognee
```

> ⚠️ **Offline gotcha (flag, test before noon):** Cognee defaults to **OpenAI** for its LLM/embeddings and will try to call out. **Configure a local provider (Ollama) and a local embedding model, and cache them on venue wifi**, or Cognee breaks the moment you go offline. Confirm a full `add → cognify → search` cycle works with the network **off**.

> **Fallback:** if Cognee fights the offline config under time pressure, a 5-line **SQLite** table delivers the same demo ("it remembered what you struggled with — locally"). Don't let the memory layer sink the build; it's the smallest of the three legs.

---

## 6. UI / screens

One laptop web app (HTML/JS or React) ↔ local Python backend over **WebSocket** (mirrors the conversation-app pattern). **Accessibility matters** (Deaf-community angle): large type, high contrast, no audio-only cues.

- **Home / Mode Select:** app name + **"On-device · No internet"** badge; two big cards **Speak** / **Sign**; footer = current language + overall progress ("12 words · 8 signs").
- **Speak:** Reachy presence indicator (calm/listening/speaking) mirroring the robot; transcript pane (chat bubbles, streaming); **correction strip** (`you said X → try Y`); push-to-talk button + text fallback; language selector.
- **Sign:** target card (big letter + BSL reference handshape) on the left; **laptop webcam panel** on the right with "detecting…" → result overlay + confidence line; word strip along the bottom (letters lighting up) + Next/Skip; Reachy reaction on correct/complete.
- **Progress (panel/overlay):** words learned, signs mastered, streak, **"Needs review"** list from Cognee.

---

## 7. Full stack & exact tooling

| Layer | Tool | Runs on | Notes |
|---|---|---|---|
| Robot control | `reachy-mini` SDK + daemon | Daemon: **robot** · SDK: **laptop** | Daemon auto-on (Wireless). `ReachyMini()` auto-connects over LAN. |
| Robot expression | `reachy-mini-emotions-library` | laptop → robot | Pre-built moves: happy, nod, etc. |
| STT | **faster-whisper** `small` int8 | laptop | Multilingual, CPU, offline. (`whisper.cpp` is a fine alternative.) |
| LLM | **Exo** (track partner) + small multilingual model | laptop | OpenAI-compatible localhost endpoint; one-line `base_url` swap. |
| TTS | **Piper** | laptop | All 3 languages have voices; CPU, real-time on modest hardware. (Kokoro 82M optional for EN/ES polish.) |
| Sign vision | **MediaPipe Hands** (`max_num_hands=2`) | laptop | 21 landmarks/hand, CPU, offline. |
| Sign classifier | **scikit-learn KNN** → tiny MLP | laptop | Train on self-recorded normalized landmarks. |
| Memory | **Cognee** (track partner), local mode | laptop | Configure local LLM/embeddings (Ollama). SQLite fallback. |
| Frontend | HTML/JS or React + WebSocket backend | laptop | Large type, high contrast. |

**Robot snippets (copy-paste base):**
```python
from reachy_mini import ReachyMini
from reachy_mini.motion.recorded_move import RecordedMoves

# Wireless + use the LAPTOP's camera/mic (robot releases its own hardware):
with ReachyMini(connection_mode="network", media_backend="no_media") as mini:
    moves = RecordedMoves("pollen-robotics/reachy-mini-emotions-library")
    mini.play_move(moves.get("happy"), initial_goto_duration=1.0)        # celebrate
    mini.goto_target(antennas=[0.5, -0.5], duration=0.4, method="minjerk")  # quick perk-up
    mini.goto_target(head=..., body_yaw=..., duration=0.6, method="minjerk")
```
*Scaffold fast:* paste `https://github.com/pollen-robotics/reachy_mini/blob/main/AGENTS.md` into Claude Code for the exact current API surface.

---

## 8. Build order — 2 people vs the real clock

**Schedule anchors:** Hacking starts **11:00** · Lunch/gate **13:00–14:00** · Feature-lock **~16:30** · **Submissions 18:30**.

**11:00–12:30 — three spikes in parallel (split across 2 people):**
- **Person B (priority): MediaPipe spike.** Webcam → 2-hand landmarks → KNN on ~5 self-recorded letters → prove it classifies offline. *This is the whole gamble.*
- **Person A: Speak lean loop.** Laptop mic → Whisper → Exo → Piper → speaker, with the tutor prompt, zero internet. Get one full corrected exchange working.
- **Either, in the gaps: robot up.** `ReachyMini()` connects over LAN, daemon dashboard reachable, one emotion plays. Confirm the **no-internet LAN** option you'll demo on.

**13:00 — GATE (decide over lunch, keep building):**
- Sign separating ≥5 letters reliably → **full dual-mode.**
- Sign still fighting → **Speak-only pivot**; Person B → harden Speak + build shell + Cognee.

**14:00–16:30 — build the chosen scope:**
- Wire each working mode into the web shell over WebSocket.
- Add spell-a-word + progress bar (Sign) / correction strip + transcript (Speak).
- Hook Cognee (or SQLite) for struggled-item logging + review list.
- Add robot reactions at the right moments (reply, correct sign, completed word).

**16:30 — FEATURE-LOCK.** No new features. **Final 90 min = rehearse the demo end-to-end, fully offline, in the exact network state you'll present in.**

---

## 9. Sponsor / track mapping

| Sponsor | Use | Status / action |
|---|---|---|
| **Exo** | Runs the Speak LLM offline at localhost. Core to the theme. | **Locked.** Confirm model string + port with reps early. |
| **Cognee** | Local memory of struggled words/signs → adaptive review. | **Locked.** Must configure offline provider (see §5). |
| **Captur** | Sign recognition as on-device image validation. | **Bonus — ask reps for a desktop/Python path before depending on it.** If none, MediaPipe stands alone (it does). |
| **Overmind** | Agent learning a new sign on-device from corrections. | **Stretch only.** |
| Cosine / Zalos | — | Skip. |

---

## 10. STRESS TEST — failure modes × mitigations

| # | Failure mode | Likelihood | Impact | Mitigation | Test by |
|---|---|---|---|---|---|
| 1 | **Sign recognition won't converge** | High | Kills the differentiator | Tiny vocab; **self-recorded clean data under venue light**; KNN first; **Speak is the fallback.** Decide at the gate. | 12:30 spike |
| 2 | **Robot unreachable when offline** (Wireless network drops) | High | Kills the robot mid-demo | Lock the no-internet LAN (robot hotspot **or** travel router); rehearse in the exact offline state. The robot link *is* the network on Wireless. | 12:30 |
| 3 | **Cognee tries to call OpenAI** when wifi dies | High | Memory leg dies offline | Configure **local Ollama** LLM+embeddings, cache them; **SQLite fallback** ready. | 13:00 |
| 4 | **Models not cached when wifi dies** | High | Whole stack dies | **Download EVERYTHING on venue wifi now** (see §11). Then test with network **off**. | Before 12:00 |
| 5 | **Conversation app assumes its HF realtime server** | Med | Wastes hours reverse-engineering | **Don't fork the realtime path — build the lean loop** (§3). Use the app only as reference. | 11:30 |
| 6 | **Noisy room kills STT** | High | Garbled transcripts | **Push-to-talk** (not always-on) + **text input fallback**. | 12:00 |
| 7 | **Bad lighting kills sign** | Med-High | Recognition flaps | Train under venue light; keep a **clean pre-recorded fallback clip**; debounce N frames before accepting. | 12:30 |
| 8 | **Two-handed BSL occlusion** (hands overlap) | Med | Misreads | Pick non-occluding handshapes for the first set; require both-hands-detected for those letters; allow Skip. | 13:00 |
| 9 | **Robot camera/mic over wifi is laggy** | Med | Sluggish Speak/Sign | **Use the laptop webcam + mic** (`media_backend="no_media"`); robot is expression-only. | 11:30 |
| 10 | **Czech (3rd lang) LLM/voice is weak** | Med | Corrections look off | **Teammate verifies live**; restrict to grammar/word-choice; **Spanish is the showcase**, Czech is the bonus. (Vietnamese already cut for tonal fragility.) | 14:00 |
| 11 | **Someone runs models on the Pi** | Med | Everything crawls | **Pi = daemon only.** Laptop = all compute + vision. State it in standup. | n/a |
| 12 | **Exo model/port assumptions wrong** | Med | LLM won't answer | Grab port from Exo log; confirm model string with reps; hardcode nothing. | 12:00 |
| 13 | **MediaPipe / MuJoCo install pain** (esp. macOS) | Med | Lost hours | Install early; on macOS prefer `pip` over `uv` for MuJoCo-adjacent deps; verify hand tracking before any ML. | Before 12:00 |
| 14 | **2 people = single points of failure** | Med | One stall blocks a whole leg | Each leg must reach a **demo-able state independently**; share the shell + WebSocket contract early so legs plug in. | 14:00 |
| 15 | **Time overrun, nothing rehearsed** | Med | Great build, bad demo | **Hard feature-lock 16:30**, 90 min rehearsal. A polished Speak-only demo beats a broken dual-mode. | 16:30 |
| 16 | **"Robot signs" expectation** | Low | Confused judges | Reachy has no hands **by design** — human signs, robot watches & reacts. Say this explicitly. | In pitch |
| 17 | **Cached libs still hit the network** (HF metadata check) | High | Hangs/throws offline despite caching | Set `HF_HUB_OFFLINE=1` + `TRANSFORMERS_OFFLINE=1`; run the full offline acceptance test (§2A). | 16:30 |
| 18 | **Emotions library fetches from HF** at runtime | Med | Robot reactions die offline | It's an HF repo ID — instantiate once online to cache, then offline flags on (§2A). | 12:00 |
| 19 | **Frontend pulls CDN assets** (fonts/JS/CSS) | Med-High | Blank/broken UI offline | Vendor everything locally — no CDN, self-host fonts (§2A). | 15:00 |
| 20 | **Laptop auto-rejoins venue wifi** | Med | Drops robot + breaks the "offline" claim mid-demo | Forget/deprioritise venue wifi; travel router or airplane-mode + local link only (§2A). | 16:30 |

---

## 11. Pre-flight checklist — download EVERYTHING now (venue wifi)

**Download + cache (needs venue wifi):**
- [ ] **faster-whisper `small`** model (run the one-liner in §3 to trigger the download)
- [ ] **Exo** running + a small multilingual model cached; note the **port + model string** from the log; confirm it answers offline
- [ ] **Piper voices**: `es_ES-*`, `en_US-*`, `cs_CZ-jirka-*` — `.onnx` + `.onnx.json` each (download explicitly, use local paths)
- [ ] **MediaPipe + OpenCV** installed; hand-landmark model cached; **2-hand tracking verified on the laptop webcam** (venue light)
- [ ] **Reachy emotions library cached** — `RecordedMoves(...)` is an **HF repo**, it downloads on first call; play one emotion offline to confirm
- [ ] **Cognee** + **Ollama** models (LLM + embedder) pulled; full `add → cognify → search` works **with internet off**
- [ ] **scikit-learn** installed; landmark-capture script ready

**Offline-proofing (the pass/fail stuff — see §2A):**
- [ ] Set **`HF_HUB_OFFLINE=1`** and **`TRANSFORMERS_OFFLINE=1`** (after caching) so HF libs don't attempt network calls
- [ ] **Vendor all frontend assets** — no CDN; self-host fonts, JS, CSS, icons
- [ ] **Pin the laptop's network** — forget/deprioritise venue wifi so it can't auto-rejoin and drop the robot
- [ ] **No-internet LAN locked** (robot hotspot OR travel router) and tested with internet off
- [ ] **`media_backend="no_media"`** confirmed (robot releases camera/mic; laptop webcam works)
- [ ] **Reachy daemon dashboard** reachable at `http://<robot-ip>:8000/docs`
- [ ] ✅ **Run the full offline acceptance test** — wifi physically off, whole demo end-to-end, nothing hangs or errors

**Content + people:**
- [ ] **Record the BSL training set** under venue lighting (30–50 samples × your letters, both hands) — make sure **H, E, L, O** are solid
- [ ] **Pre-recorded fallback clip** for Sign (in case live recognition flaps on stage)
- [ ] **Ask Captur reps** about a desktop/Python path (bonus only)
- [ ] **Confirm Exo model string + endpoint** with the Exo reps

---

## 12. Demo script (the money shot)

1. **"Everything from here is offline."** Show the offline state — pull the router's WAN / confirm you're on a local-only network (on Wireless, prove there's no internet, not just "ethernet unplugged").
2. **Speak:** say a sentence in Spanish → Reachy replies and **corrects** you; transcript + correction strip update live; Reachy emotes.
3. **Switch to Sign:** screen shows a letter → fingerspell **H‑E‑L‑L‑O** to the laptop webcam → recognition ticks green letter by letter → **Reachy celebrates** on the last one.
4. **Close on Progress:** "and it remembered what you struggled with — locally." **One tool, two communities, no internet.**

---

### One-line reminders
- **Pi = daemon only. Laptop = brain + vision + audio.**
- **Laptop webcam for Sign. Push-to-talk for Speak.**
- **Sign is the bet; Speak is the net. Decide at 13:00.**
- **"Cached" ≠ "offline." Run the whole demo with wifi physically off by 16:30 — see §2A.**
- **Spanish is the showcase; Czech is the live-verified bonus. Vietnamese cut (tonal).**
