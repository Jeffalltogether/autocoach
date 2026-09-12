import os
import json
from datetime import datetime

# Paths
PROCESSED_DIR = "/Users/jeff/Library/CloudStorage/OneDrive-Personal/git/autocoach/data/processed"
SESSIONS_JSON = "/Users/jeff/Library/CloudStorage/OneDrive-Personal/git/autocoach/frontend/public/sessions.json"

def main():
    if not os.path.exists(SESSIONS_JSON):
        sessions = []
    else:
        with open(SESSIONS_JSON, 'r') as f:
            sessions = json.load(f)
            
    existing_videos = {s.get("videoUrl") for s in sessions}
    updated = False
    
    for file in os.listdir(PROCESSED_DIR):
        if file.endswith("_tracking.json"):
            base_name = file.replace("_tracking.json", "")
            video_url = f"/data/raw/{base_name}.mp4"
            json_url = f"/data/processed/{base_name}_tracking.json"
            
            if video_url not in existing_videos:
                # Need to add new entry
                new_session = {
                    "id": base_name,
                    "name": base_name.replace("_", " ").title(),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "videoUrl": video_url,
                    "jsonUrl": json_url
                }
                sessions.insert(0, new_session) # Prepend
                updated = True
                print(f"Added {base_name} to sessions.json")
                
    if updated:
        with open(SESSIONS_JSON, 'w') as f:
            json.dump(sessions, f, indent=2)
        print("Successfully updated frontend/public/sessions.json")
    else:
        print("No new videos to add to sessions.json")

if __name__ == "__main__":
    main()
