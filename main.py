import subprocess
import threading
import time
import sys # Import sys for checking platform
import os

# Check if running on Windows for windows_capture.
# If not, this script cannot run.
if sys.platform != "win32":
    print("This script is designed to run on Windows due to 'windows_capture' dependency.")
    print("Please ensure you are running this on a Windows machine.")
    sys.exit(1)

try:
    from windows_capture import WindowsCapture, Frame, InternalCaptureControl
except ImportError:
    print("The 'windows_capture' library is not installed.")
    print("Please install it using: pip install windows-capture")
    sys.exit(1)

# Configuration
# IMPORTANT: Replace with the actual IP address of the machine running client.py
CLIENT_IP = "192.168.4.100"
PORT = 23000
# IMPORTANT: Replace with the exact title of the window you want to capture
TARGET_WINDOW_NAME = "Apex Legends" # Example: "Google Chrome", "VLC media player", etc.

ffmpeg_process = None
capture_control_ref = None
frame_counter = 0
start_time = time.time()

# Function to read FFmpeg's stderr to prevent it from blocking and provide debug info
def read_ffmpeg_stderr(process):
    for line in process.stderr:
        # You can filter or log these lines as needed
        # print(f"FFmpeg STDERR: {line.decode().strip()}")
        pass # Suppress verbose ffmpeg output for cleaner console

def start_ffmpeg_stream(width, height):
    global ffmpeg_process
    print(f"Starting FFmpeg stream with {width}x{height} resolution...")

    # The windows_capture library typically provides BGR0 or BGRA frames.
    # Assuming BGR0 for simplicity. If you encounter issues, try "bgra" and adjust ffmpeg flags.
    pix_fmt = "bgr0"

    # Ensure ffmpeg.exe is in your PATH or specify its full path
    ffmpeg_executable = "ffmpeg"
    if not os.path.exists(ffmpeg_executable) and os.name == 'nt':
        # Simple check for Windows, you might need to provide a full path if not in PATH
        print("ffmpeg.exe not found in PATH. Please ensure FFmpeg is installed and accessible.")
        print("You can download it from https://ffmpeg.org/download.html")
        sys.exit(1)


    cmd = [
        ffmpeg_executable,
        # Input arguments (raw video from stdin)
        "-f", "rawvideo",
        "-pix_fmt", pix_fmt,
        "-s", f"{width}x{height}",
        "-i", "-", # Input from stdin

        # Video encoding arguments
        "-c:v", "libx264",
        "-preset", "veryfast", # "ultrafast" for lowest CPU usage, "veryfast" for good balance
        "-crf", "20", # Constant Rate Factor: 0 is lossless, 51 is worst quality. 20-23 is good for most uses.
        "-tune", "zerolatency", # Optimize for low latency streaming
        "-maxrate", "8M", # Maximum bitrate (8 Megabits per second)
        "-bufsize", "16M", # Buffer size for rate control
        "-g", "60", # Group of pictures (GOP) size (keyframe interval)
        "-keyint_min", "60", # Minimum keyframe interval
        "-sc_threshold", "0", # Disable scene change detection for fixed GOP
        "-x264-params", "repeat-headers=1", # Ensure SPS/PPS headers are repeated for robustness

        # Output arguments (UDP stream)
        "-f", "mpegts", # MPEG Transport Stream format
        "-mpegts_flags", "+resend_headers", # Resend headers for better stream stability
        f"udp://{CLIENT_IP}:{PORT}?pkt_size=1316", # UDP address and port with common pkt_size
    ]
    try:
        ffmpeg_process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"FFmpeg process started, streaming to udp://{CLIENT_IP}:{PORT}")
        # Start a thread to read FFmpeg's stderr to prevent it from blocking
        threading.Thread(target=read_ffmpeg_stderr, args=(ffmpeg_process,), daemon=True).start()
    except FileNotFoundError:
        print(f"Error: FFmpeg executable '{ffmpeg_executable}' not found.")
        print("Please ensure FFmpeg is installed and accessible in your system's PATH.")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting FFmpeg process: {e}")
        ffmpeg_process = None

def stop_ffmpeg_stream():
    global ffmpeg_process
    if ffmpeg_process and ffmpeg_process.poll() is None:
        print("Stopping FFmpeg process...")
        try:
            ffmpeg_process.stdin.close()
            ffmpeg_process.terminate()
            ffmpeg_process.wait(timeout=5)
        except Exception as e:
            print(f"Error while stopping FFmpeg: {e}")
        finally:
            print("FFmpeg process stopped.")
    ffmpeg_process = None

def on_frame_arrived(frame: Frame, capture_control: InternalCaptureControl):
    global ffmpeg_process, capture_control_ref, frame_counter, start_time

    if capture_control_ref is None:
        capture_control_ref = capture_control

    # Check if FFmpeg process is running. If not, try to start it.
    if ffmpeg_process is None or ffmpeg_process.poll() is not None:
        # Assuming the first frame provides valid dimensions.
        # This will restart FFmpeg if it crashes, which might not be ideal but ensures recovery.
        width, height = frame.size
        print("FFmpeg process not running or crashed, attempting to restart...")
        stop_ffmpeg_stream() # Ensure any stale process is cleaned up
        start_ffmpeg_stream(width, height)
        # If restart failed, stop capture
        if ffmpeg_process is None or ffmpeg_process.poll() is not None:
            print("Failed to start FFmpeg. Stopping capture.")
            capture_control.stop()
            return

    # If FFmpeg is running, write the frame
    if ffmpeg_process and ffmpeg_process.poll() is None:
        try:
            ffmpeg_process.stdin.write(frame.buffer)
            frame_counter += 1
            if frame_counter % 30 == 0: # Print FPS every 30 frames
                elapsed_time = time.time() - start_time
                if elapsed_time > 0:
                    fps = frame_counter / elapsed_time
                    print(f"Processed {frame_counter} frames. FPS: {fps:.2f}")
        except Exception as e:
            print(f"Error writing frame to FFmpeg stdin: {e}")
            # If writing to stdin fails, FFmpeg might have crashed or pipe is broken.
            stop_ffmpeg_stream()
            capture_control.stop() # Stop capture as we can't send frames

def on_closed():
    print("Capture session closed. Stopping FFmpeg stream.")
    stop_ffmpeg_stream()

def main():
    print("Starting MarvelUDP Capture and Stream application...")
    print(f"Attempting to capture window: '{TARGET_WINDOW_NAME}'")
    print(f"Streaming to UDP: {CLIENT_IP}:{PORT}")

    if CLIENT_IP == "192.168.4.100":
        print("\nWARNING: CLIENT_IP is set to the default. Please change 'CLIENT_IP' in main.py to your client's actual IP address.")
        print("Press Ctrl+C to stop the application at any time.\n")

    try:
        # Initialize WindowsCapture
        # cursor_capture=True: includes the mouse cursor in the capture
        # draw_border=True: draws a border around the captured region (useful for debugging)
        capture = WindowsCapture(
            window_name=TARGET_WINDOW_NAME,
            cursor_capture=True,
            draw_border=True
        )
        # Assign event handlers
        capture.on_frame_arrived = on_frame_arrived
        capture.on_closed = on_closed

        print("WindowsCapture initialized. Starting capture loop...")
        capture.start() # This call blocks until the capture session is closed
    except Exception as e:
        print(f"An error occurred during capture: {e}")
    finally:
        print("Main program ending. Ensuring resources are cleaned up.")
        stop_ffmpeg_stream()
        print("Application stopped.")

if __name__ == "__main__":
    main()