import json
import os
from datetime import datetime, timezone

# Paths
PROCESSED_DIR = "/Users/jeff/Library/CloudStorage/OneDrive-Personal/git/autocoach/data/processed"
SESSIONS_JSON = "/Users/jeff/Library/CloudStorage/OneDrive-Personal/git/autocoach/frontend/public/sessions.json"

def main():
    if not os.path.exists(SESSIONS_JSON):
        sessions = []
    else:
        with open(SESSIONS_JSON, 'r') as f:
            sessions = json.load(f)
            
    existing_ids = {s.get("id") for s in sessions}
    updated = False
    
    current_files = set()
    for file in os.listdir(PROCESSED_DIR):
        if file.endswith("_tracking.json"):
            base_name = file.replace("_tracking.json", "")
            current_files.add(base_name)
            video_url = f"/data/raw/{base_name}.mp4"
            json_url = f"/data/processed/{base_name}_tracking.json"
            
            if base_name not in existing_ids:
                # Need to add new entry
                new_session = {
                    "id": base_name,
                    "name": base_name.replace("_", " ").title(),
                    "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "videoUrl": video_url,
                    "jsonUrl": json_url
                }
                sessions.insert(0, new_session) # Prepend
                updated = True
                print(f"Added {base_name} to sessions.json")
                
    # Prune stale sessions
    original_len = len(sessions)
    sessions = [s for s in sessions if s.get("id") in current_files]
    if len(sessions) < original_len:
        print(f"Removed {original_len - len(sessions)} stale sessions from sessions.json")
        updated = True

    if updated:
        with open(SESSIONS_JSON, 'w') as f:
            json.dump(sessions, f, indent=2)
        print("Successfully updated frontend/public/sessions.json")
    else:
        print("sessions.json is already up to date")

if __name__ == "__main__":
    main()
