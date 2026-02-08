import subprocess
import numpy as np
from windows_capture import WindowsCapture, Frame, InternalCaptureControl

CLIENT_IP = "192.168.4.100"
PORT = 23000

WIDTH = 1920
HEIGHT = 1080
FPS = 30
WINDOW_NAME = "Apex Legends"  # fix spelling

# FFmpeg reads raw frames from stdin (BGRA) and streams H.264 over UDP
cmd = [
    "ffmpeg",
    "-hide_banner", "-loglevel", "warning",
    "-f", "rawvideo",
    "-pix_fmt", "bgra",
    "-s", f"{WIDTH}x{HEIGHT}",
    "-r", str(FPS),
    "-i", "pipe:0",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-crf", "20",
    "-tune", "zerolatency",
    "-maxrate", "8M",
    "-bufsize", "16M",
    "-g", "60",
    "-keyint_min", "60",
    "-sc_threshold", "0",
    "-x264-params", "repeat-headers=1",
    "-f", "mpegts",
    "-mpegts_flags", "+resend_headers",
    f"udp://{CLIENT_IP}:{PORT}?pkt_size=1316",
]

ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)

capture = WindowsCapture(
    cursor_capture=None,
    draw_border=None,
    monitor_index=None,
    window_name=WINDOW_NAME,
)

@capture.event
def on_frame_arrived(frame: Frame, capture_control: InternalCaptureControl):
    # windows_capture gives BGRA (H, W, 4)
    img = frame.to_numpy(copy=False)

    # Ensure contiguous bytes for piping
    if not img.flags["C_CONTIGUOUS"]:
        img = np.ascontiguousarray(img)

    # If the captured window isn’t exactly WIDTHxHEIGHT, resize
    if img.shape[1] != WIDTH or img.shape[0] != HEIGHT:
        # simple resize using numpy -> requires opencv if you want good resize
        # easiest: change WIDTH/HEIGHT to match your actual capture size
        raise RuntimeError(f"Capture size {img.shape[1]}x{img.shape[0]} != {WIDTH}x{HEIGHT}")

    try:
        ff.stdin.write(img.tobytes())
    except BrokenPipeError:
        capture_control.stop()

@capture.event
def on_closed():
    try:
        ff.stdin.close()
    except Exception:
        pass
    ff.terminate()

capture.start()
