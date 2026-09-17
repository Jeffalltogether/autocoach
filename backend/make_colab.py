import re

with open('src/smooth_data.py', 'r') as f:
    smooth_code = f.read()
with open('src/physics.py', 'r') as f:
    physics_code = f.read()
with open('src/main.py', 'r') as f:
    main_code = f.read()

# Strip all imports from the individual files so we can just put them at the top
for imp in ["import cv2", "import numpy as np", "import json", "import argparse", "from scipy.signal import savgol_filter", "from ultralytics import YOLO", "from smooth_data import smooth_track", "from physics import apply_physics_and_events"]:
    smooth_code = smooth_code.replace(imp, "")
    physics_code = physics_code.replace(imp, "")
    main_code = main_code.replace(imp, "")

# Remove main execution block
main_code = re.sub(r'def main\(\):[\s\S]*?if __name__ == "__main__":\n\s*main\(\)', '', main_code)

colab_wrapper = f"""import json
import cv2
import numpy as np
import torch
from scipy.signal import savgol_filter
from ultralytics import YOLO

# ==========================================
# 1. Smoothing & Filtering
# ==========================================
{smooth_code}

# ==========================================
# 2. Physics & Analytics
# ==========================================
{physics_code}

# ==========================================
# 3. Main Extraction Pipeline
# ==========================================
{main_code}

# ==========================================
# RUN PIPELINE
# ==========================================
# CHANGE THESE PATHS TO YOUR GOOGLE DRIVE LOCATIONS
VIDEO_PATH = "/content/drive/MyDrive/video.mp4"
OUTPUT_JSON_PATH = "/content/drive/MyDrive/video_tracking.json"
MAX_FRAMES = None # Set to a number (e.g. 100) to test, or None for full video

# Ensure this model weight is uploaded to your Colab workspace or Google Drive
HOCKEY_MODEL_PATH = "HockeyAI_model_weight.pt" 

def run_pipeline(video_path, out_json_path, max_frames=None, homography_path=None):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading YOLO models on device: {{device}}...")
    
    pose_model = YOLO("yolov8n-pose.pt")
    hockey_model = YOLO(HOCKEY_MODEL_PATH)
    
    print("STEP 1: Running dual-model tracking extraction...")
    raw_data = extract_tracking_data(video_path, pose_model, hockey_model, max_frames)
    
    print("STEP 2: Applying Savitzky-Golay smoothing...")
    smoothed_data = smooth_all_tracks(raw_data)
    
    print("STEP 3: Applying Physics & Generating Analytics...")
    homography = None
    if homography_path:
        with open(homography_path, "r") as f:
            homography = np.array(json.load(f))
            
    final_output = apply_physics_and_events(smoothed_data, homography)
    
    with open(out_json_path, "w") as f:
        json.dump(final_output, f)
        
    print(f"Pipeline complete! Saved to {{out_json_path}}")

# run_pipeline(VIDEO_PATH, OUTPUT_JSON_PATH, MAX_FRAMES)
"""

# Clean up empty lines
colab_wrapper = re.sub(r'\n{3,}', '\n\n', colab_wrapper)

with open('colab_script.py', 'w') as f:
    f.write(colab_wrapper)
