import os
import time
import json
from flask import Flask, render_template, Response, jsonify, send_file, request

app = Flask(__name__, static_folder="static", template_folder="templates")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PREPROCESSED_DIR = os.path.join(BASE_DIR, "preprocessed")

CAMERA_INFO = [
    {"id": "CAM-01", "name": "Site Boundary West", "zone": "Zone A"},
    {"id": "CAM-02", "name": "Loading Dock Area", "zone": "Zone B"},
    {"id": "CAM-03", "name": "Main Gate Corridor", "zone": "Zone A"},
    {"id": "CAM-04", "name": "Scaffold Tower A", "zone": "Zone C"},
    {"id": "CAM-05", "name": "Equipment Storage", "zone": "Zone B"},
    {"id": "CAM-06", "name": "Material Staging", "zone": "Zone C"},
    {"id": "CAM-07", "name": "Basement Entrance", "zone": "Zone D"},
    {"id": "CAM-08", "name": "Excavation Zone", "zone": "Zone D"},
    {"id": "CAM-09", "name": "Overhead Crane Post", "zone": "Zone C"},
]

# Cache metadata in memory
META_CACHE = {}

def get_cam_meta(cam_id):
    if cam_id not in META_CACHE:
        meta_file = os.path.join(PREPROCESSED_DIR, cam_id, "meta.json")
        if os.path.exists(meta_file):
            with open(meta_file, "r") as f:
                META_CACHE[cam_id] = json.load(f)
        else:
            META_CACHE[cam_id] = None
    return META_CACHE[cam_id]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/cameras")
def api_cameras():
    cameras_list = []
    for cam in CAMERA_INFO:
        meta = get_cam_meta(cam["id"])
        frames_count = len(meta["frames_meta"]) if meta else 0
        total_violations = sum(f.get("violations", 0) for f in meta["frames_meta"]) if meta else 0
        cameras_list.append({
            "id": cam["id"],
            "name": cam["name"],
            "zone": cam["zone"],
            "frames_count": frames_count,
            "has_violations": total_violations > 0,
            "total_violations": total_violations
        })
    return jsonify({"cameras": cameras_list})

@app.route("/api/camera/<cam_id>/stats")
def api_camera_stats(cam_id):
    meta = get_cam_meta(cam_id)
    if not meta:
        return jsonify({"error": "Camera not found"}), 404
    return jsonify(meta)

def generate_mjpeg_stream(cam_id):
    """Streams the pre-rendered 5 FPS frames in an infinite seamless loop."""
    cam_dir = os.path.join(PREPROCESSED_DIR, cam_id)
    if not os.path.exists(cam_dir):
        return
        
    meta = get_cam_meta(cam_id)
    total_frames = meta["total_frames"] if meta else 50
    fps = meta.get("fps", 5.0) if meta else 5.0
    frame_interval = 1.0 / fps # 0.20s per frame for true 5 FPS playback

    # Pre-read frame bytes into RAM for ultra-low latency streaming
    frame_bytes_cache = []
    for i in range(total_frames):
        fpath = os.path.join(cam_dir, f"frame_{i:04d}.jpg")
        if os.path.exists(fpath):
            with open(fpath, "rb") as f:
                frame_bytes_cache.append(f.read())

    if not frame_bytes_cache:
        return

    frame_idx = 0
    cache_len = len(frame_bytes_cache)

    while True:
        t0 = time.time()
        frame_data = frame_bytes_cache[frame_idx]
        frame_idx = (frame_idx + 1) % cache_len

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame_data + b"\r\n")

        elapsed = time.time() - t0
        sleep_time = max(0.01, frame_interval - elapsed)
        time.sleep(sleep_time)

@app.route("/stream/<cam_id>")
def stream_camera(cam_id):
    return Response(
        generate_mjpeg_stream(cam_id),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
