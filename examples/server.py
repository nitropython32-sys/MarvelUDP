# server_wc_udp.py
import socket, struct, time
import cv2
import numpy as np
from windows_capture import WindowsCapture, Frame, InternalCaptureControl

CLIENT_IP = "192.168.4.100"
PORT = 23000
WINDOW_NAME = "Marvel Rivals"

# UDP sizing
MAX_DGRAM = 1400  # safe on LAN/WiFi
# Header: frame_id (I), chunk_id (H), total_chunks (H), jpg_len (I)
HDR_FMT = "!IHHI"
HDR_SIZE = struct.calcsize(HDR_FMT)
PAYLOAD_MAX = MAX_DGRAM - HDR_SIZE

# JPEG tuning (speed vs quality)
JPG_QUALITY = 70  # raise to 85 if you want sharper, but bigger frames

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

capture = WindowsCapture(window_name=WINDOW_NAME)
frame_id = 0

@capture.event
def on_frame_arrived(frame: Frame, capture_control: InternalCaptureControl):
    global frame_id

    img = frame.frame_buffer  # BGRA: (H, W, 4)

    # BGRA -> BGR (OpenCV expects BGR)
    bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    ok, enc = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), JPG_QUALITY])
    if not ok:
        return

    data = enc.tobytes()
    jpg_len = len(data)

    total = (jpg_len + PAYLOAD_MAX - 1) // PAYLOAD_MAX

    # Send chunks (each chunk self-identifies frame + position)
    for chunk_id in range(total):
        start = chunk_id * PAYLOAD_MAX
        payload = data[start:start + PAYLOAD_MAX]
        header = struct.pack(HDR_FMT, frame_id, chunk_id, total, jpg_len)
        sock.sendto(header + payload, (CLIENT_IP, PORT))

    frame_id = (frame_id + 1) & 0xFFFFFFFF  # wrap safely

@capture.event
def on_closed():
    try:
        sock.close()
    except Exception:
        pass

capture.start()
