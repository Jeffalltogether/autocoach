import os
import subprocess
import argparse
import json
import numpy as np
from physics import apply_physics_and_events

def main():
    parser = argparse.ArgumentParser(description="Autocoach Batch Processor")
    parser.add_argument("-f", "--force-yolo", action="store_true", help="Force recompute YOLO on all videos")
    parser.add_argument("-p", "--force-physics", action="store_true", help="Force recompute physics on all existing JSONs")
    parser.add_argument("-s", "--skip-new", action="store_true", help="Skip unprocessed raw videos")
    args = parser.parse_args()

    INPUT_DIR = "/content/drive/MyDrive/autocoach/raw_videos"
    OUTPUT_DIR = "/content/drive/MyDrive/autocoach/processed_data"
    CALIBRATION_DIR = "/content/drive/MyDrive/autocoach/calibration"

    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Scanning for videos in {INPUT_DIR}...")
    videos = [f for f in os.listdir(INPUT_DIR) if f.endswith('.mp4')]

    if not videos:
        print("No .mp4 videos found in the raw_videos folder!")
        
    for video in videos:
        base_name = os.path.splitext(video)[0]
        video_path = os.path.join(INPUT_DIR, video)
        out_json = os.path.join(OUTPUT_DIR, f"{base_name}_tracking.json")
        homography_path = os.path.join(CALIBRATION_DIR, f"{base_name}_homography.json")
        roi_path = os.path.join(CALIBRATION_DIR, f"{base_name}_roi.json")
        
        json_exists = os.path.exists(out_json)
        
        run_yolo = False
        run_physics_only = False
        
        if args.force_yolo:
            run_yolo = True
        elif not json_exists:
            if not args.skip_new:
                run_yolo = True
            else:
                print(f"⏭️ Skipping new video '{video}' (--skip-new)")
                continue
        else:
            if args.force_physics:
                run_physics_only = True
            else:
                print(f"⏭️ Skipping '{video}' - Already processed!")
                continue
                
        if run_yolo:
            print(f"\n🎬 Processing YOLO + Physics for '{video}'...")
            cmd = ["python", "/content/main.py", "--video", video_path, "--out_json", out_json]
            if os.path.exists(homography_path):
                cmd.extend(["--homography", homography_path])
            if os.path.exists(roi_path):
                cmd.extend(["--roi", roi_path])
            subprocess.run(cmd, check=True)
            print(f"✅ Finished full pipeline for '{video}'")
            
        elif run_physics_only:
            print(f"\n⚡ Recomputing Physics for '{video}'...")
            try:
                with open(out_json, 'r') as f:
                    data = json.load(f)
                
                fps = data.get("metadata", {}).get("fps", 30)
                frames_data = data.get("frames", data)
                
                homography_matrix = None
                if os.path.exists(homography_path):
                    with open(homography_path, 'r') as f:
                        h_data = json.load(f)
                        homography_matrix = np.array(h_data["homography_matrix"], dtype=np.float32)
                
                final_output = apply_physics_and_events(frames_data, homography_matrix, fps)
                
                with open(out_json, 'w') as f:
                    json.dump(final_output, f, indent=2)
                print(f"✅ Finished physics update for '{video}'")
            except Exception as e:
                print(f"❌ Error updating physics for '{video}': {e}")
                
    print("\n🎉 Batch processing complete!")

if __name__ == "__main__":
    main()
