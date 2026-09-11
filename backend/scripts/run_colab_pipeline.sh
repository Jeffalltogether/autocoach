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

echo "⚙️ Executing Dual-Model Pipeline..."
# Run the script on the VM using Jupyter shell magic so we can pass command-line arguments
echo "!python /content/main.py --video \"$DRIVE_VIDEO_PATH\" --out_json \"$DRIVE_JSON_PATH\" --out_video \"$DRIVE_OUTPUT_PATH\"" | ~/.local/bin/colab exec -s $SESSION_NAME --timeout 3600

echo "🛑 Tearing down session..."
~/.local/bin/colab stop -s $SESSION_NAME

echo "✅ Pipeline Complete! Check your Google Drive."
