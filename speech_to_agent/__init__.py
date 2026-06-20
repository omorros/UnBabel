"""speech_to_agent — a standalone spike proving the OffBabel Speak leg in isolation:

    push-to-talk mic  ->  faster-whisper (STT)  ->  two-step tutor agent on Exo  ->  {reply, correction}

No web UI, no robot, no memory — just the speech->agent core, so it can be de-risked on its own
(PRD section 8, the 11:00 spike) before it's wired into offbabel/server.py over the WebSocket.

Run the whole loop:   python -m speech_to_agent.loop
Preflight everything:  python -m speech_to_agent.doctor
"""
