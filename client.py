import socket
import time

UDP_IP = "192.168.4.102"
UDP_PORT = 5005
MESSAGE = b"Hello, Server!"

sock = socket.socket(socket.AF_INET,  # Internet
                     socket.SOCK_DGRAM)  # UDP

while True:
    print(f"Sending message: {MESSAGE}")
    sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))
    time.sleep(30)
