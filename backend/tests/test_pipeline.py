import os
import subprocess

import cv2
import numpy as np
import pytest


@pytest.fixture
def dummy_video(tmp_path):
    # Create a 5-frame dummy video for CI testing
    video_path = tmp_path / "dummy_test.mp4"
    out = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*'mp4v'), 30, (640, 480))
    for _ in range(5):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        out.write(frame)
    out.release()
    return str(video_path)

def test_pipeline_dry_run(dummy_video, tmp_path):
    # Run the main pipeline for 2 frames to ensure imports and logic don't crash
    out_json = tmp_path / "dummy_test_tracking.json"
    
    cmd = [
        "python", "src/main.py",
        "--video", dummy_video,
        "--out_json", str(out_json),
        "--frames", "2",
        "--device", "cpu"  # Force CPU for CI/CD runners without GPUs
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    
    assert result.returncode == 0, f"Pipeline crashed:\n{result.stderr}"
    assert os.path.exists(out_json), "Tracking JSON was not generated"
