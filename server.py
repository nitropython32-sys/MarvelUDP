# sender.py  (run on the machine with the webcam)
import subprocess

CLIENT_IP = "192.168.4.100"
PORT = 23000

cmd = [
    "ffmpeg",
    "-f", "v4l2",
    "-input_format", "mjpeg",
    "-framerate", "30",
    "-video_size", "1920x1080",
    "-i", "/dev/video0",
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

subprocess.run(cmd, check=True)
