import os
import cv2
import json
import time
from ultralytics import YOLO

downloads_dir = r"C:\Users\debji\Downloads"
output_base = r"C:\Users\debji\Downloads\cctv_app\preprocessed"
model_path = r"C:\Users\debji\Downloads\yolo26_training\ppe_yolo26s\weights\best.pt"

target_timestamps = [
    ("CAM-01", "Site Boundary West", "20261025161147"),
    ("CAM-02", "Loading Dock Area", "20261025160837"),
    ("CAM-03", "Main Gate Corridor", "20261025160719"),
    ("CAM-04", "Scaffold Tower A", "20261025160603"),
    ("CAM-05", "Equipment Storage", "20261025160429"),
    ("CAM-06", "Material Staging", "20261025160319"),
    ("CAM-07", "Basement Entrance", "20261025160152"),
    ("CAM-08", "Excavation Zone", "20261025160043"),
    ("CAM-09", "Overhead Crane Post", "20261025154636"),
]

all_files = os.listdir(downloads_dir)
cameras = []

for cam_id, loc, ts in target_timestamps:
    match_file = None
    for f in all_files:
        if ts in f and f.endswith(".mp4"):
            match_file = os.path.join(downloads_dir, f)
            break
    cameras.append({
        "id": cam_id,
        "name": loc,
        "timestamp": ts,
        "video_path": match_file
    })

print(f"Found {len(cameras)} cameras. Loading YOLO model: {model_path}...")
model = YOLO(model_path)

# Custom color palette for PPE classes
# Classes: 3: head_nohelmet, 4: head_whelmet, 5: no_vest, 6: person, 7: vest
# Alerts: head_nohelmet (Red), no_vest (Orange), head_whelmet (Green), vest (Cyan), person (Yellow)
CLASS_COLORS = {
    0: (128, 128, 128),
    1: (128, 128, 128),
    2: (128, 128, 128),
    3: (0, 0, 230),      # head_nohelmet - Bright Red (Violation!)
    4: (0, 200, 0),      # head_whelmet - Bright Green (Compliant)
    5: (0, 140, 255),    # no_vest - Amber / Orange (Violation!)
    6: (255, 200, 0),    # person - Yellow
    7: (230, 200, 0),    # vest - Cyan / Aqua (Compliant)
}

CLASS_NAMES = {
    0: "10", 1: "11", 2: "12",
    3: "NO HELMET",
    4: "HELMET",
    5: "NO VEST",
    6: "PERSON",
    7: "VEST"
}

cams_summary = []

for idx, cam in enumerate(cameras):
    cam_id = cam["id"]
    video_path = cam["video_path"]
    cam_dir = os.path.join(output_base, cam_id)
    os.makedirs(cam_dir, exist_ok=True)
    
    print(f"\n[{idx+1}/9] Pre-processing {cam_id}: {cam['name']}...")
    if not video_path or not os.path.exists(video_path):
        print(f"  [ERROR] Video file not found: {video_path}")
        continue
    
    cap = cv2.VideoCapture(video_path)
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_raw_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_raw_frames / video_fps
    
    target_fps = 5.0
    total_target_frames = int(duration * target_fps) # e.g. 50 frames for 10s
    
    metadata = {
        "cam_id": cam_id,
        "name": cam["name"],
        "duration": duration,
        "fps": target_fps,
        "total_frames": total_target_frames,
        "frames_meta": []
    }
    
    saved_count = 0
    t_start = time.time()
    
    for frame_idx in range(total_target_frames):
        target_raw_frame = int(round(frame_idx * (video_fps / target_fps)))
        if target_raw_frame >= total_raw_frames:
            break
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_raw_frame)
        ret, frame = cap.read()
        if not ret:
            break
        
        # Resize frame to clean HD aspect ratio for smooth UI streaming (854x480)
        h, w = frame.shape[:2]
        frame_resized = cv2.resize(frame, (854, 480))
        
        # YOLO inference
        results = model.predict(frame_resized, imgsz=480, conf=0.25, verbose=False)[0]
        
        violations_count = 0
        persons_count = 0
        helmets_count = 0
        vests_count = 0
        
        detections = []
        for box in results.boxes:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            xyxy = [int(v) for v in box.xyxy[0].tolist()]
            
            c_name = CLASS_NAMES.get(cls_id, f"ID_{cls_id}")
            color = CLASS_COLORS.get(cls_id, (255, 255, 255))
            
            if cls_id in (3, 5): # Violations: no helmet, no vest
                violations_count += 1
            if cls_id == 6:
                persons_count += 1
            elif cls_id == 4:
                helmets_count += 1
            elif cls_id == 7:
                vests_count += 1
                
            detections.append({
                "class_id": cls_id,
                "label": c_name,
                "conf": round(conf, 2),
                "box": xyxy
            })
            
            # Draw bounding box
            x1, y1, x2, y2 = xyxy
            # Thicker box for violations
            thickness = 2 if cls_id not in (3, 5) else 3
            cv2.rectangle(frame_resized, (x1, y1), (x2, y2), color, thickness)
            
            # Badge text
            label_text = f"{c_name} {conf*100:.0f}%"
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame_resized, (x1, max(0, y1 - 18)), (x1 + tw + 6, max(18, y1)), color, -1)
            cv2.putText(frame_resized, label_text, (x1 + 3, max(14, y1 - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0) if color != (0, 0, 230) else (255, 255, 255), 1, cv2.LINE_AA)
            
        # Draw CCTV HUD overlay
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        hud_cam = f"● REC | {cam_id} - {cam['name'].upper()}"
        cv2.putText(frame_resized, hud_cam, (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2, cv2.LINE_AA)
        
        status_text = "SAFETY ALERT" if violations_count > 0 else "STATUS: NORMAL"
        status_color = (0, 0, 240) if violations_count > 0 else (0, 230, 0)
        cv2.putText(frame_resized, f"[{status_text}]", (15, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 2, cv2.LINE_AA)
        
        # Save output image
        img_name = f"frame_{frame_idx:04d}.jpg"
        img_path = os.path.join(cam_dir, img_name)
        cv2.imwrite(img_path, frame_resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        metadata["frames_meta"].append({
            "frame_idx": frame_idx,
            "violations": violations_count,
            "persons": persons_count,
            "helmets": helmets_count,
            "vests": vests_count,
            "detections": detections
        })
        saved_count += 1
        
    cap.release()
    elapsed = time.time() - t_start
    print(f"  -> Generated {saved_count} frames in {elapsed:.1f}s ({elapsed/saved_count*1000:.0f}ms/frame)")
    
    meta_path = os.path.join(cam_dir, "meta.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
        
    cams_summary.append({
        "cam_id": cam_id,
        "name": cam["name"],
        "frames": saved_count
    })

# Save global config
with open(os.path.join(output_base, "cameras.json"), "w") as f:
    json.dump(cams_summary, f, indent=2)

print("\n=== All 9 Cameras Preprocessed at 5 FPS successfully! ===")
