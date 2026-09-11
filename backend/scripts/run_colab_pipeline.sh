#!/bin/bash
# Exit on error
set -e

SESSION_NAME="autocoach"

# Ensure the video paths match the Google Drive structure you created
DRIVE_VIDEO_PATH="/content/drive/MyDrive/autocoach/raw_videos/pro_game.mp4"
DRIVE_JSON_PATH="/content/drive/MyDrive/autocoach/processed_data/pro_game_tracking.json"
DRIVE_OUTPUT_PATH="/content/drive/MyDrive/autocoach/processed_data/pro_game_output.mp4"

echo "🚀 Checking for existing Colab GPU Session ($SESSION_NAME)..."
if ~/.local/bin/colab status -s $SESSION_NAME >/dev/null 2>&1; then
    echo "✅ Session '$SESSION_NAME' is already running! Skipping provisioning."
else
    echo "🚀 Provisioning new Colab GPU Session ($SESSION_NAME)..."
    ~/.local/bin/colab new -s $SESSION_NAME --gpu T4
fi

echo "📂 Mounting Google Drive..."
# Mounts drive. If it's your first time, it might pause here for browser authentication.
~/.local/bin/colab drivemount -s $SESSION_NAME

echo "📦 Installing Dependencies from pyproject.toml..."
~/.local/bin/colab install -s $SESSION_NAME -r pyproject.toml

echo "🧠 Checking for HockeyAI Model in Google Drive..."
echo "
import os
from huggingface_hub import hf_hub_download

drive_model_dir = '/content/drive/MyDrive/autocoach/models'
os.makedirs(drive_model_dir, exist_ok=True)
model_path = os.path.join(drive_model_dir, 'HockeyAI_model_weight.pt')

if not os.path.exists(model_path):
    print('Downloading model to Google Drive for persistent storage...')
    hf_hub_download(repo_id='SimulaMet-HOST/HockeyAI', filename='HockeyAI_model_weight.pt', local_dir=drive_model_dir)
else:
    print('✅ Model found in Google Drive! Skipping download.')
" | ~/.local/bin/colab exec -s $SESSION_NAME

echo "⚙️ Uploading backend code to Colab..."
~/.local/bin/colab upload -s $SESSION_NAME src/main.py /content/main.py
~/.local/bin/colab upload -s $SESSION_NAME src/batch_process.py /content/batch_process.py

echo "⚙️ Executing Batch Pipeline..."
# Run the batch script which automatically skips already processed videos
echo "!python /content/batch_process.py" | ~/.local/bin/colab exec -s $SESSION_NAME --timeout 7200

echo "📥 Zipping and Downloading Processed Results to Local Machine..."
LOCAL_DATA_DIR="/Users/jeff/Library/CloudStorage/OneDrive-Personal/git/autocoach/data/processed"
mkdir -p "$LOCAL_DATA_DIR"

# Zip the contents of the processed_data folder on Colab
echo "!cd /content/drive/MyDrive/autocoach/processed_data && zip -q -r /content/processed_results.zip ." | ~/.local/bin/colab exec -s $SESSION_NAME

# Download the zip file directly to the Mac
~/.local/bin/colab download -s $SESSION_NAME /content/processed_results.zip ./processed_results.zip

# Unzip locally and clean up
unzip -o -q ./processed_results.zip -d "$LOCAL_DATA_DIR"
rm ./processed_results.zip
echo "✅ Downloaded all processed files to $LOCAL_DATA_DIR"

echo "🛑 Tearing down session..."
~/.local/bin/colab stop -s $SESSION_NAME

echo "✅ Pipeline Complete!"
