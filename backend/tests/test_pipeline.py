import os
import json
import pytest
from pathlib import Path
import subprocess

def test_pipeline_smoke():
    """Run the main.py pipeline on a tiny test video to ensure no crashes."""
    
    test_video = Path(__file__).parent / "fixtures" / "test_video.mp4"
    out_json = Path(__file__).parent / "fixtures" / "test_output.json"
    
    # Ensure test video exists
    assert test_video.exists(), "Test fixture video is missing."
    
    # Clean up old outputs
    if out_json.exists():
        out_json.unlink()
        
    import sys
    from unittest.mock import patch, MagicMock
    
    # Ensure src is in sys.path so 'from physics import ...' works
    src_path = str(Path(__file__).parent.parent / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
        
    from src.main import main
    
    # Mock YOLO so we don't load huge models in CI
    with patch("src.main.YOLO") as mock_yolo:
        # Create a mock model instance that returns an empty list for tracking
        mock_model_instance = MagicMock()
        mock_model_instance.track.return_value = [MagicMock(boxes=None, keypoints=None)]
        mock_yolo.return_value = mock_model_instance
        
        # Patch sys.argv to simulate CLI args
        test_args = [
            "main.py",
            "--video", str(test_video),
            "--out_json", str(out_json),
            "--frames", "5"
        ]
        
        with patch.object(sys, "argv", test_args):
            try:
                main()
            except Exception as e:
                pytest.fail(f"Pipeline crashed: {e}")
    
    # Assert JSON was created
    assert out_json.exists(), "JSON output was not created."
    with open(out_json, "r") as f:
        data = json.load(f)
        
    assert isinstance(data, dict)
    assert "frames" in data
    assert len(data["frames"]) > 0
    assert "frame" in data["frames"][0]
    assert "players" in data["frames"][0]
    
    # Clean up generated files
    out_json.unlink()
