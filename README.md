# Autocoach

Video analysis system for youth ice hockey practices and scrimmages.

## Architecture

This project is split into two main components based on our offline-processing architecture:

### 1. `backend/` (Python)
An asynchronous/batch data pipeline for computer vision tasks. 
- **Ingestion & Calibration:** OpenCV processing to correct GoPro fisheye distortion.
- **Detection & Identification:** YOLO/AprilTag detection to identify players.
- **Output:** Dense JSON/Parquet coordinate data mapped to a 2D rink surface.

### 2. `frontend/` (React / Vite)
A web-based interactive dashboard hosted on Vercel that relies on the master video and the processed JSON metadata to:
- Render trajectory overlays over the video.
- Present heuristic analytics (speed, distance, etc.).
- Proxy Google Drive URLs directly using Vercel Edge Functions.

### 3. `data/`
Local directory for storing raw video files and output JSON coordinate manifests. (Ignored in version control).

## Development Setup

**Backend (Python):**
Requires Python 3.10+. We recommend using `uv` for dependency management.
```bash
cd backend
uv sync
uv run pytest
```

**Frontend (React/Vite):**
Requires Node.js.
```bash
cd frontend
npm install
npm run dev
```

## Vercel Deployment & Observability

This project is configured for static hosting on Vercel. 
To stream the live build and runtime logs straight to your terminal during deployment:
```bash
npm install -g vercel
vercel link
vercel logs
```
