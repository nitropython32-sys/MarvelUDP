# receiver.py (run on the client/viewer machine)
import subprocess

PORT = 23000

cmd = [
    "ffplay",
    "-flags", "low_delay",
    f"udp://0.0.0.0:{PORT}",
]

subprocess.run(cmd, check=True)
