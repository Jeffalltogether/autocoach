import os
import subprocess

INPUT_DIR = "/content/drive/MyDrive/autocoach/raw_videos"
OUTPUT_DIR = "/content/drive/MyDrive/autocoach/processed_data"

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
    
    # Check if this video has already been processed
    if os.path.exists(out_json):
        print(f"⏭️ Skipping '{video}' - Already processed!")
        continue
        
    print(f"\n🎬 Processing '{video}'...")
    cmd = [
        "python", "/content/main.py", 
        "--video", video_path, 
        "--out_json", out_json
    ]
    
    # Pass homography if it exists in the output directory
    homography_path = os.path.join(OUTPUT_DIR, f"{base_name}_homography.json")
    if os.path.exists(homography_path):
        cmd.extend(["--homography", homography_path])
        print("   -> Attached Homography (Physics / MPH)")
    
    # Run the main.py script for this specific video
    subprocess.run(cmd, check=True)
    print(f"✅ Finished processing '{video}'")
    
print("\n🎉 Batch processing complete!")
