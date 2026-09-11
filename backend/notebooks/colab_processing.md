# Autocoach Google Colab Processing

This guide contains the code cells you can copy and paste into a [Google Colab](https://colab.research.google.com/) notebook to process your videos using free GPUs and save the results directly to your Google Drive.

## Setup Instructions
1. Go to [Google Colab](https://colab.research.google.com/) and create a **New Notebook**.
2. At the top right, click **Connect** -> **Change runtime type**, select **T4 GPU**, and click **Save**.
3. Create new code cells and paste the following snippets into them.

---

### Cell 1: Mount Google Drive
This cell will prompt you to log into your Google Account to grant Colab access to your 2TB Google Drive.
```python
from google.colab import drive
import os

# Mount Google Drive
drive.mount('/content/drive')

# Define your Google Drive paths (Update these to match your Drive structure)
DRIVE_INPUT_DIR = '/content/drive/MyDrive/autocoach/raw_videos'
DRIVE_OUTPUT_DIR = '/content/drive/MyDrive/autocoach/processed_data'

# Create directories if they don't exist
os.makedirs(DRIVE_INPUT_DIR, exist_ok=True)
os.makedirs(DRIVE_OUTPUT_DIR, exist_ok=True)

print(f"✅ Google Drive mounted successfully!")
```

### Cell 2: Setup Autocoach Backend
This cell will clone your GitHub repository and install the backend dependencies using `uv`.
```bash
%%bash
# Clone the repository
git clone https://github.com/Jeffalltogether/autocoach.git
cd autocoach

# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Install backend dependencies
cd backend
uv pip install --system -r pyproject.toml
```

### Cell 3: Process Videos
This cell will look for `.mp4` videos in your `raw_videos` folder on Google Drive, run the Autocoach backend script on them, and output the tracking JSON and processed videos back to Google Drive.
```python
import os
import subprocess

# Define paths
BACKEND_SRC = '/content/autocoach/backend/src/main.py'

print(f"Scanning for videos in: {DRIVE_INPUT_DIR}")
video_files = [f for f in os.listdir(DRIVE_INPUT_DIR) if f.endswith('.mp4')]

if not video_files:
    print("No videos found! Please upload some .mp4 files to your Google Drive.")
else:
    for video in video_files:
        input_path = os.path.join(DRIVE_INPUT_DIR, video)
        output_prefix = os.path.join(DRIVE_OUTPUT_DIR, video.replace('.mp4', ''))
        
        json_path = os.path.join(DRIVE_OUTPUT_DIR, video.replace('.mp4', '.json'))
        video_out_path = os.path.join(DRIVE_OUTPUT_DIR, video.replace('.mp4', '_processed.mp4'))
        
        print(f"\nProcessing: {video}")
        # Run the backend main.py script
        cmd = [
            "python", BACKEND_SRC, 
            "--video", input_path, 
            "--out_json", json_path,
            "--out_video", video_out_path
        ]

        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Successfully processed {video}")
        else:
            print(f"❌ Error processing {video}:")
            print(result.stderr)
            
print("\nBatch processing complete!")
```

## Integrating with the Frontend
Once the videos are processed and the JSON data is saved to `MyDrive/autocoach/processed_data`, you can download those files and place them in your frontend's `public/` directory for Vercel to serve, or eventually set up an API to fetch them dynamically!
