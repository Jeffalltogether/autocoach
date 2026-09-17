import json
import numpy as np
from src.physics import apply_physics_and_events

def process_file(json_path, homography_path, fps=30):
    print(f"Updating {json_path}...")
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    frames_data = data.get("frames", data)
    
    homography_matrix = None
    if homography_path:
        with open(homography_path, 'r') as f:
            h_data = json.load(f)
            homography_matrix = np.array(h_data["homography_matrix"], dtype=np.float32)
            
    final_output = apply_physics_and_events(frames_data, homography_matrix, fps)
    
    with open(json_path, 'w') as f:
        json.dump(final_output, f, indent=2)

try:
    process_file('../data/processed/LiveBarn_14sec_practice_tracking.json', '../data/calibration/LiveBarn_14sec_practice_homography.json')
    process_file('../data/processed/static_hockey_dev_6to9_tracking.json', '../data/calibration/static_hockey_dev_6to9_homography.json')
    print("Done!")
except Exception as e:
    print(f"Error: {e}")
