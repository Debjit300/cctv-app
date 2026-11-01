# SENTINEL-AI CCTV Monitoring System

## Overview
A real-time styled CCTV Surveillance & PPE Compliance monitoring web application powered by our trained **YOLO26s** model.

## Features
- **4 Videos per Page (2x2 Grid)**:
  - **Page 1**: `CAM-01` to `CAM-04`
  - **Page 2**: `CAM-05` to `CAM-08`
  - **Page 3**: `CAM-09` (Single focused feed)
- **Pre-rendered 5 FPS Looping**:
  - All 9 videos were pre-processed using the trained YOLO26s checkpoint (`best.pt`) at 5 FPS with bounding boxes and HUD metadata.
  - Video streams are served via seamless MJPEG streams looping in real-time.
- **Safety Violation Highlighting**:
  - Cards automatically glow red with `SAFETY VIOLATION DETECTED` badges when workers lack helmets (`head_nohelmet`) or vests (`no_vest`).
- **Interactive Features**:
  - Click any camera feed or the **ENLARGE ⛶** button to pop open a high-res inspection view.
  - Use top buttons, pagination arrows, or keyboard arrow keys (`←`, `→`, `ESC`) to switch pages.
  - Fullscreen mode support (`⛶ FULLSCREEN`).

## Accessing the Dashboard
- Local URL: **[http://localhost:5000](http://localhost:5000)**
- LAN / Mobile URL: **http://192.168.0.234:5000**
