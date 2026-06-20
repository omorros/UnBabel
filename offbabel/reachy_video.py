"""Reachy Mini live camera -> browser MJPEG bridge.

The robot exposes no RTSP server, so we run `rpicam-vid` on the robot over SSH (MJPEG to stdout),
reparse the JPEG frames here, and hand them to the browser as multipart/x-mixed-replace — which a
plain <img> tag renders with no extra client code.

    Reachy camera -> rpicam-vid MJPEG over SSH -> this reader thread -> /reachy-media/video.mjpeg -> <img>

One shared SSH stream feeds all browser clients (a refcount starts it on the first viewer and stops
it when the last one leaves, so the robot isn't streaming to nobody). Best-effort throughout: a
missing tunnel/robot prints and degrades to "no frames" — it must never crash the server (the robot
is an enhancement, not a dependency).
"""
import subprocess
import threading
import time

from . import config

JPEG_SOI = b"\xff\xd8"  # start-of-image marker
JPEG_EOI = b"\xff\xd9"  # end-of-image marker

_MAX_BUFFER = 4 * 1024 * 1024  # drop a runaway buffer if we never find a frame boundary (corrupt stream)


class ReachyVideoStreamer:
    """Owns the SSH/rpicam subprocess and the most-recent JPEG frame. Thread-safe."""

    def __init__(self):
        self._proc = None
        self._reader = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._clients = 0
        self.latest_frame = None
        self.last_frame_time = 0.0

    def _command(self):
        remote = (
            "rpicam-vid -t 0 --codec mjpeg --inline "
            f"--width {config.REACHY_CAM_WIDTH} "
            f"--height {config.REACHY_CAM_HEIGHT} "
            f"--framerate {config.REACHY_CAM_FPS} "
            "-o -"
        )
        # BatchMode=yes: never block the server on a password/passphrase prompt — fail fast instead.
        # Keepalives detect a dropped LAN/tunnel so the reader thread exits and can be restarted.
        return [
            "ssh", "-T",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=5",
            "-o", "ServerAliveInterval=5",
            "-o", "ServerAliveCountMax=2",
            "-o", "StrictHostKeyChecking=accept-new",
            config.REACHY_SSH_HOST,
            remote,
        ]

    def start(self):
        """Spawn the SSH/rpicam stream if it isn't already running. Safe to call repeatedly."""
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                return
            self._stop.clear()
            self.latest_frame = None
            self.last_frame_time = 0.0
            try:
                self._proc = subprocess.Popen(
                    self._command(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,
                    bufsize=0,
                )
            except Exception as e:  # noqa: BLE001
                print("reachy video: failed to spawn ssh/rpicam (ignored):", e)
                self._proc = None
                return
            self._reader = threading.Thread(target=self._read_loop, args=(self._proc,), daemon=True)
            self._reader.start()

    def stop(self):
        """Terminate the stream and reader thread. Safe to call repeatedly."""
        with self._lock:
            self._stop.set()
            proc = self._proc
            self._proc = None
            self._reader = None
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

    def add_client(self):
        """A browser connected: start the shared stream on the first viewer."""
        with self._lock:
            self._clients += 1
        self.start()

    def remove_client(self):
        """A browser disconnected: stop the shared stream when the last viewer leaves."""
        with self._lock:
            self._clients = max(0, self._clients - 1)
            idle = self._clients == 0
        if idle:
            self.stop()

    def get_latest_frame(self):
        with self._lock:
            return self.latest_frame

    def is_alive(self):
        with self._lock:
            return self._proc is not None and self._proc.poll() is None

    def status(self):
        with self._lock:
            return {
                "alive": self._proc is not None and self._proc.poll() is None,
                "has_frame": self.latest_frame is not None,
                "last_frame_time": self.last_frame_time,
                "clients": self._clients,
                "ssh_host": config.REACHY_SSH_HOST,
                "width": config.REACHY_CAM_WIDTH,
                "height": config.REACHY_CAM_HEIGHT,
                "framerate": config.REACHY_CAM_FPS,
            }

    def _read_loop(self, proc):
        """Read rpicam's MJPEG stdout, split it on JPEG SOI/EOI markers, publish the latest frame."""
        buffer = b""
        if proc.stdout is None:
            return
        try:
            while not self._stop.is_set():
                chunk = proc.stdout.read(4096)
                if not chunk:
                    break  # EOF: ssh/rpicam exited (tunnel dropped, camera busy, etc.)
                buffer += chunk
                while True:
                    start = buffer.find(JPEG_SOI)
                    if start < 0:
                        if len(buffer) > _MAX_BUFFER:
                            buffer = b""
                        break
                    end = buffer.find(JPEG_EOI, start + 2)
                    if end < 0:
                        if start > 0:
                            buffer = buffer[start:]  # discard pre-SOI garbage, keep the partial frame
                        break
                    frame = buffer[start:end + 2]
                    buffer = buffer[end + 2:]
                    with self._lock:
                        self.latest_frame = frame
                        self.last_frame_time = time.monotonic()
        except Exception as e:  # noqa: BLE001
            print("reachy video: reader stopped (ignored):", e)
        finally:
            with self._lock:
                if self._proc is proc:
                    self._proc = None


# Module-level singleton: one shared stream for the whole server.
streamer = ReachyVideoStreamer()