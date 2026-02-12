# client_udp_video.py
import socket, struct, time
import cv2
import numpy as np

LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 5005
MAX_DGRAM = 1400

HDR_FMT = "!IHH"
HDR_SIZE = struct.calcsize(HDR_FMT)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LISTEN_IP, LISTEN_PORT))
sock.settimeout(0.5)

# frame_id -> { "t0": time, "total": N, "chunks": dict(chunk_id -> bytes), "received": count }
frames = {}
LATEST_FRAME = -1

FRAME_TIMEOUT_SEC = 0.25  # drop incomplete frames after 250ms

while True:
    now = time.time()

    # Drop old/incomplete frames
    for fid in list(frames.keys()):
        if now - frames[fid]["t0"] > FRAME_TIMEOUT_SEC:
            del frames[fid]

    try:
        packet, _ = sock.recvfrom(MAX_DGRAM)
    except socket.timeout:
        continue

    if len(packet) < HDR_SIZE:
        continue

    frame_id, chunk_id, total = struct.unpack(HDR_FMT, packet[:HDR_SIZE])
    payload = packet[HDR_SIZE:]

    # If we already moved past this frame, ignore late packets
    if frame_id < LATEST_FRAME:
        continue

    # If a newer frame arrives, drop older frames (prevents "sync drift"/latency buildup)
    if frame_id > LATEST_FRAME:
        # keep only this newest frame (optional, but good for low latency)
        frames = {frame_id: frames.get(frame_id, {"t0": now, "total": total, "chunks": {}, "received": 0})}
        LATEST_FRAME = frame_id

    if frame_id not in frames:
        frames[frame_id] = {"t0": now, "total": total, "chunks": {}, "received": 0}

    f = frames[frame_id]
    if chunk_id not in f["chunks"]:
        f["chunks"][chunk_id] = payload
        f["received"] += 1

    if f["received"] == f["total"]:
        # Assemble in order
        data = b"".join(f["chunks"][i] for i in range(f["total"]))
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if img is not None:
            cv2.imshow("UDP Video", img)
            if cv2.waitKey(1) == 27:
                break

        del frames[frame_id]
