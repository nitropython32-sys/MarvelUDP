from windows_capture import WindowsCapture, Frame
import inspect


capture = WindowsCapture(window_name="Marvel Rivals")


print("capture type:", type(capture))
print("capture dir (filtered):",
      [x for x in dir(capture) if not x.startswith("_")])


@capture.event
def on_frame_arrived(frame: Frame, _):
    print("\n--- on_frame_arrived ---")
    print("frame type:", type(frame))
    print("frame dir (filtered):",
          [x for x in dir(frame) if not x.startswith("_")])


    # Common metadata
    for name in ["width", "height"]:
        if hasattr(frame, name):
            print(f"frame.{name} =", getattr(frame, name))


    # Try common buffer attributes
    for name in ["frame_buffer", "buffer", "data", "raw"]:
        if hasattr(frame, name):
            val = getattr(frame, name)
            try:
                print(f"type(frame.{name}) =", type(val), "len =", len(val))
            except Exception as e:
                print(f"type(frame.{name}) =", type(val), "len = <error>", e)


    # Try common numpy conversion method names
    candidates = ["to_numpy", "as_numpy", "numpy", "to_ndarray", "as_ndarray"]
    for m in candidates:
        if hasattr(frame, m) and callable(getattr(frame, m)):
            print("has method:", m)


    # If there IS a conversion method, try it and print shape/dtype
    for m in candidates:
        if hasattr(frame, m) and callable(getattr(frame, m)):
            try:
                arr = getattr(frame, m)()
                print(f"{m}() type:", type(arr))
                if hasattr(arr, "shape"):
                    print(f"{m}() shape:", arr.shape)
                if hasattr(arr, "dtype"):
                    print(f"{m}() dtype:", arr.dtype)
            except Exception as e:
                print(f"{m}() failed:", repr(e))


    # Stop after first frame so it doesn't spam
    # (remove if you want continuous)
    # _.stop()  # not always available here depending on binding


@capture.event
def on_closed():
    print("capture closed")


capture.start()
