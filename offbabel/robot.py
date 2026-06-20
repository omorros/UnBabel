"""Reachy Mini wrapper. Best-effort by design: if the robot or its library is absent or
offline, every call is a safe no-op so the demo never crashes. The on-screen avatar carries
the emotion either way (PRD: robot = enhancement, not dependency).

Call connect() once on the Mac (the demo machine). The server imports emote() which is always
safe to call. Fill in real moves once the emotions library is cached on the Mac.

Emotion contract (shared with the UI 'emote' event): idle | listening | speaking | happy | nod
"""
_mini = None
_moves = None

EMOTION_TO_MOVE = {
    "happy": "happy",
    "nod": "nod",
    "speaking": "nod",   # placeholder until we pick a talking motion
    "listening": None,   # handled as a pose, not a recorded move
    "idle": None,
}


def connect():
    """Connect over the no-internet LAN and release the robot camera/mic so the laptop owns them."""
    global _mini, _moves
    try:
        from reachy_mini import ReachyMini
        from reachy_mini.motion.recorded_move import RecordedMoves

        _mini = ReachyMini(connection_mode="network", media_backend="no_media").__enter__()
        _moves = RecordedMoves("pollen-robotics/reachy-mini-emotions-library")
        print("Reachy connected.")
    except Exception as e:  # noqa: BLE001
        print("Reachy not connected (UI avatar will carry emotion):", e)
        _mini = None
        _moves = None


def emote(emotion):
    if _mini is None or _moves is None:
        return
    move_name = EMOTION_TO_MOVE.get(emotion)
    if not move_name:
        return
    try:
        _mini.play_move(_moves.get(move_name), initial_goto_duration=0.8)
    except Exception as e:  # noqa: BLE001
        print("play_move failed (ignored):", e)
