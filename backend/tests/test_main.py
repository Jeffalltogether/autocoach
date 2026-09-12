import pytest
import numpy as np
from src.main import smooth_track, infer_stick_vector

def test_smooth_track_basic():
    """Test that smoothing works on a basic array."""
    data = np.array([1.0, 2.0, 3.0, 10.0, 5.0, 6.0, 7.0])
    smoothed = smooth_track(data, window_length=5, polyorder=2)
    
    # The outlier (10.0) should be smoothed down, keeping it closer to the trend
    assert len(smoothed) == len(data)
    assert smoothed[3] < 9.0  # Should be smoothed downwards

def test_smooth_track_short_array():
    """Test that smoothing handles arrays shorter than the window length safely."""
    data = np.array([1.0, 2.0])
    smoothed = smooth_track(data, window_length=5, polyorder=2)
    # If window_length <= polyorder, it returns original data
    assert np.array_equal(smoothed, data)

def generate_mock_keypoints(l_wrist, r_wrist):
    """Helper to generate a mock 17-keypoint COCO array."""
    kpts = [{"x": 0.0, "y": 0.0, "conf": 0.0} for _ in range(17)]
    kpts[9] = l_wrist
    kpts[10] = r_wrist
    return kpts

def test_infer_stick_vector_valid():
    """Test stick vector inference with valid wrist keypoints."""
    # Top hand is higher up (lower Y), so Left Wrist is top hand here
    l_wrist = {"x": 100, "y": 100, "conf": 0.9}
    r_wrist = {"x": 120, "y": 120, "conf": 0.9}
    kpts = generate_mock_keypoints(l_wrist, r_wrist)
    
    stick = infer_stick_vector(kpts)
    
    assert stick is not None
    assert stick["top_hand"]["x"] == 100
    assert stick["top_hand"]["y"] == 100
    assert stick["bottom_hand"]["x"] == 120
    assert stick["bottom_hand"]["y"] == 120
    
    # dx = 20, dy = 20, extension = 1.5
    # blade_x = 120 + (20 * 1.5) = 150
    # blade_y = 120 + (20 * 1.5) = 150
    assert stick["blade"]["x"] == 150
    assert stick["blade"]["y"] == 150

def test_infer_stick_vector_low_confidence():
    """Test that inference aborts if confidence is too low."""
    l_wrist = {"x": 100, "y": 100, "conf": 0.3} # Below 0.4 threshold
    r_wrist = {"x": 120, "y": 120, "conf": 0.9}
    kpts = generate_mock_keypoints(l_wrist, r_wrist)
    
    stick = infer_stick_vector(kpts)
    assert stick is None
