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

# gui_demo.py
import subprocess
import threading
import queue

import numpy as np
from PIL import Image, ImageTk

import tkinter as tk
from tkinter import ttk


# ----------------------------
# Video receive/decode settings
# ----------------------------
PORT = 23000

# IMPORTANT: do NOT name these W/H (tk.W is a sticky constant)
VID_W, VID_H = 1280, 720
PIX_FMT = "rgb24"                 # raw RGB frames
BYTES_PER_FRAME = VID_W * VID_H * 3


# 1-slot queue => realtime (drop old frames if UI falls behind)
frame_q: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=1)


def ffmpeg_receiver():
    """
    Receives a UDP stream, decodes it, and outputs raw RGB frames to stdout.
    We read fixed-size frames and push them into a tiny queue.
    """
    cmd = [
        "ffmpeg",
        "-hide_banner", "-loglevel", "error",

        # low-latency-ish flags (best effort; depends on stream)
        "-fflags", "nobuffer",
        "-flags", "low_delay",
        "-probesize", "32",
        "-analyzeduration", "0",

        # input
        "-i", f"udp://0.0.0.0:{PORT}?fifo_size=1000000&overrun_nonfatal=1",

        # no audio
        "-an",

        # force output size + pixel format for deterministic frame size
        "-vf", f"scale={VID_W}:{VID_H}",
        "-f", "rawvideo",
        "-pix_fmt", PIX_FMT,

        # stdout
        "pipe:1",
    ]

    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=10**7,
    )

    stdout = p.stdout
    if stdout is None:
        return

    while True:
        raw = stdout.read(BYTES_PER_FRAME)
        if len(raw) != BYTES_PER_FRAME:
            break  # stream ended or ffmpeg exited

        frame = np.frombuffer(raw, dtype=np.uint8).reshape((VID_H, VID_W, 3))

        # Drop old frame if behind
        try:
            if frame_q.full():
                frame_q.get_nowait()
            frame_q.put_nowait(frame)
        except queue.Empty:
            pass
        except queue.Full:
            pass


def build_gui():
    root = tk.Tk()
    root.title("Clean GUI Demo")
    root.geometry("800x800")

    mainframe = ttk.Frame(root, padding=(3, 3, 12, 12))
    mainframe.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

    central_frame = ttk.Frame(mainframe, relief="raised", borderwidth=2)
    central_frame.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

    # This label is where frames actually display (you can't draw into a Frame directly)
    video_label = ttk.Label(central_frame)
    video_label.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
    central_frame.columnconfigure(0, weight=1)
    central_frame.rowconfigure(0, weight=1)

    action_button = ttk.Button(mainframe, text="Click Me", width=20)
    action_button.grid(column=0, row=1, pady=10)

    # Expand layout
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    mainframe.columnconfigure(0, weight=1)
    mainframe.rowconfigure(0, weight=1)

    for child in mainframe.winfo_children():
        child.grid_configure(padx=5, pady=5)

    return root, video_label


def main():
    root, video_label = build_gui()

    # Receiver thread
    threading.Thread(target=ffmpeg_receiver, daemon=True).start()

    # UI pump: runs on Tk main thread
    def ui_pump():
        try:
            frame = frame_q.get_nowait()
        except queue.Empty:
            root.after(5, ui_pump)
            return

        # Convert frame -> Tk image
        img = Image.fromarray(frame)  # frame is RGB uint8
        tkimg = ImageTk.PhotoImage(img)

        video_label.configure(image=tkimg)
        video_label.image = tkimg  # keep reference

        root.after(5, ui_pump)

    ui_pump()
    root.mainloop()


if __name__ == "__main__":
    main()
