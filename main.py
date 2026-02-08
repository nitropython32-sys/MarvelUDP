import subprocess
from windows_capture import WindowsCapture, Frame, InternalCaptureControl

CLIENT_IP = "192.168.4.100"
PORT = 23000
FPS = 30
WINDOW_NAME = "Apex Legends"   # must match real window title

ff = None
W = H = None

capture = WindowsCapture(
    cursor_capture=None,
    draw_border=None,
    monitor_index=None,
    window_name=WINDOW_NAME,
)

@capture.event
def on_frame_arrived(frame: Frame, capture_control: InternalCaptureControl):
    global ff, W, H

    img = frame.to_numpy(copy=False)  # typically BGRA, shape (H, W, 4)

    if ff is None:
        H, W = img.shape[0], img.shape[1]

        cmd = [
            "ffmpeg",
            "-hide_banner", "-loglevel", "warning",
            "-f", "rawvideo",
            "-pix_fmt", "bgra",
            "-s", f"{W}x{H}",
            "-r", str(FPS),
            "-i", "pipe:0",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-tune", "zerolatency",
            "-g", str(FPS * 2),
            "-keyint_min", str(FPS * 2),
            "-sc_threshold", "0",
            "-x264-params", "repeat-headers=1",
            "-f", "mpegts",
            "-mpegts_flags", "+resend_headers",
            f"udp://{CLIENT_IP}:{PORT}?pkt_size=1316",
        ]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    try:
        ff.stdin.write(img.tobytes())
    except BrokenPipeError:
        capture_control.stop()

@capture.event
def on_closed():
    global ff
    if ff:
        try:
            ff.stdin.close()
        except Exception:
            pass
        ff.terminate()

capture.start()
