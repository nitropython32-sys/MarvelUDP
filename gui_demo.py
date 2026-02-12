# from tkinter import *
# from tkinter import ttk

# root = Tk()
# root.title("Clean GUI Demo")
# root.geometry("800x800") # Set initial window size

# mainframe = ttk.Frame(root, padding=(3, 3, 12, 12))
# mainframe.grid(column=0, row=0, sticky=(N, W, E, S))

# # Add your widgets here
# central_frame = ttk.Frame(mainframe, relief="raised", borderwidth=2) # Added relief and border for visibility
# central_frame.grid(column=0, row=0, sticky=(N, W, E, S))

# # Placeholder label inside the central_frame
# ttk.Label(central_frame, text="This is the central frame").grid(column=0, row=0, sticky=(N, W, E, S))
# central_frame.columnconfigure(0, weight=1)
# central_frame.rowconfigure(0, weight=1)

# action_button = ttk.Button(mainframe, text="Click Me", width=20)
# action_button.grid(column=0, row=1, pady=10) # Added some padding

# # Configure mainframe to give weight to the central_frame's row
# mainframe.rowconfigure(0, weight=1)

# root.columnconfigure(0, weight=1)
# root.rowconfigure(0, weight=1)
# mainframe.columnconfigure(0, weight=1) # Adjust column configure for a single column layout
# for child in mainframe.winfo_children():
#     child.grid_configure(padx=5, pady=5)

# root.mainloop()


# Source - https://stackoverflow.com/a/72149815
# Posted by Art
# Retrieved 2026-02-08, License - CC BY-SA 4.0
# Source - https://stackoverflow.com/a/68089310
# Posted by Shihab
# Retrieved 2026-02-08, License - CC BY-SA 4.0

# from tkinter import *
# from tkvideo import tkvideo

# root = Tk()
# my_label = Label(root)
# my_label.pack()
# player = tkvideo("/home/nigel/Videos/Screencasts/Screencast from 2026-02-08 18-29-13.webm", my_label, loop = 1, size = (1280,720))
# player.play()

# root.mainloop()

import subprocess
import threading
import queue
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageTk, ImageOps

import tkinter as tk
from tkinter import ttk

PORT = 23000

# stream decode output (fixed raw frames)
VID_W, VID_H = 1280, 720
PIX_FMT = "rgb24"
BYTES_PER_FRAME = VID_W * VID_H * 3

frame_q = queue.Queue(maxsize=1)

# holds the most recent frame (RGB uint8 numpy)
latest_frame = {"frame": None}

def ffmpeg_receiver():
    cmd = [
        "ffmpeg",
        "-hide_banner", "-loglevel", "error",
        "-fflags", "nobuffer",
        "-flags", "low_delay",
        "-probesize", "32",
        "-analyzeduration", "0",
        "-i", f"udp://0.0.0.0:{PORT}?fifo_size=1000000&overrun_nonfatal=1",
        "-an",
        "-vf", f"scale={VID_W}:{VID_H}",
        "-f", "rawvideo",
        "-pix_fmt", PIX_FMT,
        "pipe:1",
    ]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**7)
    out = p.stdout
    if out is None:
        return

    while True:
        raw = out.read(BYTES_PER_FRAME)
        if len(raw) != BYTES_PER_FRAME:
            break

        frame = np.frombuffer(raw, dtype=np.uint8).reshape((VID_H, VID_W, 3))

        # keep realtime
        if frame_q.full():
            try: frame_q.get_nowait()
            except queue.Empty: pass
        try: frame_q.put_nowait(frame)
        except queue.Full: pass

def build_gui():
    root = tk.Tk()
    root.title("Viewer")
    root.geometry("800x800")

    mainframe = ttk.Frame(root, padding=(3, 3, 12, 12))
    mainframe.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

    central_frame = ttk.Frame(mainframe, relief="raised", borderwidth=2)
    central_frame.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

    video_label = ttk.Label(central_frame)
    video_label.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

    # Let widgets expand with window
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    mainframe.columnconfigure(0, weight=1)
    mainframe.rowconfigure(0, weight=1)
    central_frame.columnconfigure(0, weight=1)
    central_frame.rowconfigure(0, weight=1)

    # Track label size so the display auto-fits
    target = {"w": 640, "h": 360}
    def on_resize(e):
        if e.width > 1 and e.height > 1:
            target["w"], target["h"] = e.width, e.height
    video_label.bind("<Configure>", on_resize)

    return root, mainframe, video_label, target

def main():
    root, mainframe, video_label, target = build_gui()

    # Where to save snapshots
    out_dir = Path.home() / "Pictures" / "snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    def snapshot(_event=None):
        frame = latest_frame["frame"]
        if frame is None:
            print("No frame yet.")
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = out_dir / f"snapshot_{ts}.png"

        Image.fromarray(frame).save(path)
        print("Saved", path)

    # Button
    snap_btn = ttk.Button(mainframe, text="Snapshot (Ctrl+S)", command=snapshot)
    snap_btn.grid(column=0, row=1, pady=10)

    # Keybind (Ctrl+S)
    root.bind("<Control-s>", snapshot)
    root.bind("<Control-S>", snapshot)

    threading.Thread(target=ffmpeg_receiver, daemon=True).start()

    def ui_pump():
        try:
            frame = frame_q.get_nowait()
        except queue.Empty:
            root.after(5, ui_pump)
            return

        # store latest raw frame for snapshotting (no resize)
        latest_frame["frame"] = frame

        # display resized to widget
        img = Image.fromarray(frame)
        img = ImageOps.pad(img, (target["w"], target["h"]), method=Image.Resampling.LANCZOS)

        tkimg = ImageTk.PhotoImage(img)
        video_label.configure(image=tkimg)
        video_label.image = tkimg

        root.after(5, ui_pump)

    ui_pump()
    root.mainloop()

if __name__ == "__main__":
    main()


