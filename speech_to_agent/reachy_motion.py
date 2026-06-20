"""Single-owner robot motion for the Speak loop + the "Reachy is thinking…" idle animation.

The agent takes a few seconds to answer. Instead of a dead pause, Reachy does a gentle idle gesture
so the wait reads as "pausing to think", not "broken" — latency turned into personality.

ONE OWNER for robot motion (important): the thinking loop, the speaking wobble, and any future head
tracking must never send move commands at the same time or Reachy jumps and fights itself. Every
mover takes the single module-level lock via `claim()`. The thinking loop holds it for its whole run
and releases it — after returning to neutral — when stopped, so speaking can take the body cleanly.

Motion is a smooth SINE loop (continuous, not 1-2-3-4 poses): mostly antennas, a little head yaw,
tiny roll/pitch, no aggressive tilt. Commands overlap (sent every STEP_SECONDS, each lasting
MOVE_DURATION) with minjerk interpolation so it flows as one gesture.

Talks to the Reachy daemon over HTTP (same tunnel as reachy_speaker.py). Fails soft everywhere:
no robot / no tunnel must never break the conversation loop.
"""
import math
import threading
import time

import requests

from . import config

# ---- motion tunables ----
ANTENNA_AMP = 0.30
CYCLE_SECONDS = 2.4
STEP_SECONDS = 0.18        # send a new command this often...
MOVE_DURATION = 0.30       # ...each lasting this long, so they overlap and blend
HEAD_YAW_AMP = 0.065
HEAD_ROLL_AMP = 0.020
HEAD_PITCH_BASE = 0.0      # center the nod at level (was -0.014, which read as "head tilted down")
HEAD_PITCH_AMP = 0.007     # gentle downward nod only (0 .. -0.007)
HEAD_Z_BASE = 0.0
HEAD_Z_AMP = 0.0           # head-height bob; 0 = off (keep it calm, no aggressive tilting)

NEUTRAL_ANTENNAS = [-0.1745, 0.1745]
CENTER_LEFT, CENTER_RIGHT = NEUTRAL_ANTENNAS
# Rest pose Reachy returns to when thinking stops, just before speaking: head fully level (0,0,0).
NEUTRAL_HEAD = {"x": 0.0, "y": 0.0, "z": 0.0, "roll": 0.0, "pitch": 0.0, "yaw": 0.0}

# ---- the ONE owner of robot motion ----
_motion_lock = threading.Lock()


class claim:
    """Context manager for exclusive robot-motion ownership. Wrap ANY block that moves the robot.
        with claim():                  -> block until free
        with claim(timeout=2.0):       -> wait up to 2s, then proceed best-effort
        with claim(blocking=False) as got:  -> skip if someone else is moving the robot
    """

    def __init__(self, blocking=True, timeout=-1.0):
        self._blocking = blocking
        self._timeout = timeout
        self.held = False

    def __enter__(self):
        self.held = (_motion_lock.acquire(True, self._timeout) if self._blocking
                     else _motion_lock.acquire(False))
        return self.held

    def __exit__(self, *exc):
        if self.held:
            _motion_lock.release()
            self.held = False
        return False


def _goto(antennas, head, duration, interpolation="minjerk", timeout=2.0):
    # NOTE: this is the daemon move request body. The head pose MUST go under "head_pose" — the
    # /api/move/goto schema ignores an unknown "head" key and falls back to a default (down-tilted)
    # pose, so the head never follows what we compute here. Everything routes through here.
    body = {"antennas": list(antennas), "head_pose": head,
            "duration": duration, "interpolation": interpolation}
    requests.post(f"{config.REACHY_API_BASE}/api/move/goto",
                  json=body, timeout=timeout).raise_for_status()


def neutral(duration=0.5):
    """Return antennas + head to the rest pose."""
    _goto(NEUTRAL_ANTENNAS, dict(NEUTRAL_HEAD), duration)


def _frame(t):
    """Sine-driven antenna + head pose at time t seconds since the loop started. Continuous."""
    phase = math.sin((2 * math.pi * t) / CYCLE_SECONDS)
    soft_phase = math.sin((math.pi * t) / CYCLE_SECONDS)   # slower, gentle nod (not synced to antennas)
    antennas = [CENTER_LEFT + ANTENNA_AMP * phase, CENTER_RIGHT + ANTENNA_AMP * phase]
    head = {
        "x": 0.0, "y": 0.0,
        "z": HEAD_Z_BASE + HEAD_Z_AMP * abs(soft_phase),
        "roll": -HEAD_ROLL_AMP * phase,
        "pitch": HEAD_PITCH_BASE - HEAD_PITCH_AMP * abs(soft_phase),
        "yaw": HEAD_YAW_AMP * phase,
    }
    return antennas, head


class ThinkingMotion:
    """Gentle 'thinking' idle loop. start() while the agent generates; stop() when the answer is
    ready (it returns to neutral). Holds the motion lock for its whole run so nothing else moves
    the robot meanwhile. Best-effort: if the robot is unreachable it quietly does nothing."""

    def __init__(self):
        self._thread = None
        self._stop = threading.Event()
        # start()/stop() are called from BOTH the asyncio loop (_run_tutor/_voice_turn) and the mic
        # listener thread (on_speech_end). Serialize them so concurrent calls can't orphan the motion
        # thread (which would keep holding the motion lock and silently kill all future 'thinking').
        self._guard = threading.Lock()

    def start(self):
        with self._guard:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, name="reachy-thinking", daemon=True)
            self._thread.start()

    def _run(self):
        with claim(blocking=False) as got:
            if not got:
                return  # someone else owns motion right now — skip rather than fight
            t0 = time.monotonic()
            moved = False
            try:
                while not self._stop.is_set():
                    antennas, head = _frame(time.monotonic() - t0)
                    try:
                        _goto(antennas, head, MOVE_DURATION)
                        moved = True
                    except Exception as e:  # noqa: BLE001
                        if not moved:
                            print(f"  (Reachy motion offline: {e})", flush=True)
                            return  # robot unreachable: don't spam commands for the whole gap
                        # transient hiccup mid-gesture — ignore and keep flowing
                    self._stop.wait(STEP_SECONDS)
            finally:
                if moved:
                    try:
                        neutral(duration=0.35)
                        time.sleep(0.4)  # let the head fully reach level (0,0,0) before speaking
                    except Exception:  # noqa: BLE001
                        pass

    def stop(self):
        with self._guard:
            self._stop.set()
            t, self._thread = self._thread, None
        if t:
            t.join(timeout=3.0)  # joined outside the guard so a slow neutral() never blocks a start()


# one shared instance = one owner across the app
thinking = ThinkingMotion()
