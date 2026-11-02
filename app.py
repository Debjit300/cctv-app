import os
import time
import json
import logging
from flask import Flask, render_template, Response, jsonify

# Configure clean logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CCTV-LiveServer")

app = Flask(__name__, static_folder="static", template_folder="templates")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PREPROCESSED_DIR = os.path.join(BASE_DIR, "preprocessed")

# CCTV Camera Topology Definition
CAMERA_TOPOLOGY = [
    {"id": "CAM-01", "name": "Site Boundary West", "zone": "Zone A", "feed_uri": "rtsp://site-cam-01/live"},
    {"id": "CAM-02", "name": "Loading Dock Area", "zone": "Zone B", "feed_uri": "rtsp://site-cam-02/live"},
    {"id": "CAM-03", "name": "Main Gate Corridor", "zone": "Zone A", "feed_uri": "rtsp://site-cam-03/live"},
    {"id": "CAM-04", "name": "Scaffold Tower A", "zone": "Zone C", "feed_uri": "rtsp://site-cam-04/live"},
    {"id": "CAM-05", "name": "Equipment Storage", "zone": "Zone B", "feed_uri": "rtsp://site-cam-05/live"},
    {"id": "CAM-06", "name": "Material Staging", "zone": "Zone C", "feed_uri": "rtsp://site-cam-06/live"},
    {"id": "CAM-07", "name": "Basement Entrance", "zone": "Zone D", "feed_uri": "rtsp://site-cam-07/live"},
    {"id": "CAM-08", "name": "Excavation Zone", "zone": "Zone D", "feed_uri": "rtsp://site-cam-08/live"},
    {"id": "CAM-09", "name": "Overhead Crane Post", "zone": "Zone C", "feed_uri": "rtsp://site-cam-09/live"},
]

# In-memory fast ring-buffer cache for video stream frames
FRAME_BUFFER_CACHE = {}
METADATA_CACHE = {}

def load_camera_buffers():
    """Initializes in-memory ring buffers for all cameras to support concurrent high-throughput MJPEG distribution."""
    logger.info("Initializing in-memory frame buffers for all 9 CCTV channels...")
    for cam in CAMERA_TOPOLOGY:
        cam_id = cam["id"]
        cam_dir = os.path.join(PREPROCESSED_DIR, cam_id)
        meta_file = os.path.join(cam_dir, "meta.json")
        
        frames_list = []
        if os.path.exists(cam_dir):
            for i in range(50):
                img_path = os.path.join(cam_dir, f"frame_{i:04d}.jpg")
                if os.path.exists(img_path):
                    with open(img_path, "rb") as f:
                        frames_list.append(f.read())
        
        FRAME_BUFFER_CACHE[cam_id] = frames_list
        logger.info(f"Loaded buffer for {cam_id}: {len(frames_list)} frames.")

        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r") as mf:
                    METADATA_CACHE[cam_id] = json.load(mf)
            except Exception:
                METADATA_CACHE[cam_id] = None
        else:
            METADATA_CACHE[cam_id] = None

# Initialize buffers on start
load_camera_buffers()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/cameras")
def api_cameras():
    cameras_list = []
    for cam in CAMERA_TOPOLOGY:
        cam_id = cam["id"]
        meta = METADATA_CACHE.get(cam_id)
        frames_count = len(FRAME_BUFFER_CACHE.get(cam_id, []))
        total_violations = sum(f.get("violations", 0) for f in meta.get("frames_meta", [])) if meta else 0
        
        cameras_list.append({
            "id": cam_id,
            "name": cam["name"],
            "zone": cam["zone"],
            "fps": 5.0,
            "status": "ONLINE",
            "frames_count": frames_count,
            "has_violations": total_violations > 0,
            "total_violations": total_violations
        })
    return jsonify({"cameras": cameras_list, "timestamp": time.time()})

@app.route("/api/camera/<cam_id>/stats")
def api_camera_stats(cam_id):
    meta = METADATA_CACHE.get(cam_id)
    if not meta:
        return jsonify({"error": "Camera not found or uninitialized"}), 404
    return jsonify(meta)

def generate_live_mjpeg_feed(cam_id):
    """
    Simulates real-time 5 FPS streaming from the model inference pipeline
    with zero buffering latency. Each connected client gets a synced loop.
    """
    frames = FRAME_BUFFER_CACHE.get(cam_id, [])
    if not frames:
        logger.warning(f"No frames in buffer for {cam_id}")
        return

    frame_count = len(frames)
    frame_interval = 0.20  # 5 FPS (200ms per frame)
    idx = 0

    while True:
        t_start = time.time()
        frame_bytes = frames[idx]
        idx = (idx + 1) % frame_count

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n"
               b"Content-Length: " + str(len(frame_bytes)).encode() + b"\r\n\r\n"
               + frame_bytes + b"\r\n")

        elapsed = time.time() - t_start
        sleep_dur = frame_interval - elapsed
        if sleep_dur > 0:
            time.sleep(sleep_dur)
        else:
            time.sleep(0.01)

@app.route("/stream/<cam_id>")
def stream_camera(cam_id):
    # Disable caching headers completely for MJPEG
    response = Response(
        generate_live_mjpeg_feed(cam_id),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, pre-check=0, post-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
