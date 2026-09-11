# Autocoach

Video analysis system for youth ice hockey practices and scrimmages.

## Architecture

This project is split into two main components based on our offline-processing architecture:

### 1. `backend/` (Python)
An asynchronous/batch data pipeline for computer vision tasks. 
- **Ingestion & Calibration:** OpenCV processing to correct GoPro fisheye distortion.
- **Detection & Identification:** YOLO/AprilTag detection to identify players.
- **Output:** Dense JSON/Parquet coordinate data mapped to a 2D rink surface.

### 2. `frontend/` (Rust / WebGPU / WASM)
A web-based interactive dashboard that relies on the master video and the processed JSON metadata to:
- Render trajectory overlays.
- Provide timestamp jumping for specific events.
- Present heuristic analytics (speed, distance, etc.).

### 3. `data/`
Local directory for storing raw video files and output JSON coordinate manifests. (Ignored in version control).

## Development Setup

**Backend (Python):**
Requires Python 3.10+. We recommend using `uv` for dependency management.
```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -e .
```

**Frontend (Rust):**
Requires Rust and Cargo.
```bash
cd frontend
cargo build
```
