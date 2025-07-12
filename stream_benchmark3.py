import gi
import time
import csv
import re

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

Gst.init(None)

# Parameters
VIDEO_PATH = "/data/video.mp4"
DETECTION_MODEL = "/models/detection/person-detection-retail-0013.xml"
CLASSIFICATION_MODEL = "/models/classification/person-attributes-recognition-crossroad-0230.xml"
DEVICE = "CPU"  # replace CPU with GPU for GPU 

# stream branch
def build_stream(index):
    return f"""
        filesrc location={VIDEO_PATH} !
        decodebin !
        videoconvert !
        gvadetect model={DETECTION_MODEL} device={DEVICE} !
        gvaclassify model={CLASSIFICATION_MODEL} device={DEVICE} !
        queue !
        gvametaconvert !
        gvafpscounter name=fps{index} !
        fakesink sync=false
    """

# === Parse FPS from logs ===
def extract_fps(log):
    lines = log.strip().splitlines()
    for line in reversed(lines):
        if "FpsCounter" in line and "total=" in line and "per-stream=" in line:
            try:
                total = float(re.search(r"total=(\d+\.?\d*) fps", line).group(1))
                per_stream = float(re.search(r"per-stream=(\d+\.?\d*) fps", line).group(1))
                return total, per_stream
            except:
                continue
    return 0.0, 0.0

# === Run benchmark for the given stream count ===
def run_pipeline(num_streams):
    print(f"\n==============================")
    print(f" Running pipeline with {num_streams} stream(s) on {DEVICE}")
    print(f"==============================")

    pipeline_str = " ".join([build_stream(i) for i in range(num_streams)])
    pipeline = Gst.parse_launch(pipeline_str)
    bus = pipeline.get_bus()
    pipeline.set_state(Gst.State.PLAYING)

    log_output = []
    timeout_sec = 30
    start_time = time.time()

    while True:
        msg = bus.timed_pop_filtered(1000 * Gst.MSECOND, Gst.MessageType.ELEMENT | Gst.MessageType.ERROR | Gst.MessageType.EOS)
        if msg:
            if msg.type == Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                print(f"[ERROR] {err}: {debug}")
                break
            elif msg.type == Gst.MessageType.ELEMENT:
                struct = msg.get_structure()
                if struct and struct.has_name("fps"):
                    log_output.append(struct.to_string())

        if time.time() - start_time > timeout_sec:
            print("[INFO] Timeout reached.")
            break

    pipeline.set_state(Gst.State.NULL)
    full_log = "\n".join(log_output)

    print("[DEBUG] GStreamer output:")
    print(full_log)

    total_fps, per_stream_fps = extract_fps(full_log)
    print(f"Completed run for {num_streams} stream(s)")
    
    return total_fps, per_stream_fps

# === Main benchmark ===
stream_counts = [1, 2, 4, 8]
results = []

for count in stream_counts:
    total, per_stream = run_pipeline(count)
    results.append([DEVICE, count, total, per_stream])



