# server_udp_video.py
import socket, struct, time
import cv2
import numpy as np

DEST_IP = "192.168.1.100"   # client
DEST_PORT = 5005
MAX_DGRAM = 1400

# Header: frame_id (I), chunk_id (H), total_chunks (H)
HDR_FMT = "!IHH"
HDR_SIZE = struct.calcsize(HDR_FMT)
PAYLOAD_MAX = MAX_DGRAM - HDR_SIZE

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

cap = cv2.VideoCapture(0)
frame_id = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    ok, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    if not ok:
        continue

    data = jpg.tobytes()
    total = (len(data) + PAYLOAD_MAX - 1) // PAYLOAD_MAX

    for chunk_id in range(total):
        start = chunk_id * PAYLOAD_MAX
        payload = data[start:start + PAYLOAD_MAX]
        header = struct.pack(HDR_FMT, frame_id, chunk_id, total)
        sock.sendto(header + payload, (DEST_IP, DEST_PORT))

    frame_id = (frame_id + 1) & 0xFFFFFFFF
