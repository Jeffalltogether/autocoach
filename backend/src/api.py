import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional

app = FastAPI(title="Autocoach API", description="API for Player Tracking and Roster Assignments")

# Configure CORS so the React frontend can talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local dev (React is usually on 3000 or 5173)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Base path for storing assignments
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/assignments"))
os.makedirs(DATA_DIR, exist_ok=True)

# --- Pydantic Models for Validation ---

class RosterPlayer(BaseModel):
    id: str
    name: str
    jersey: Optional[str] = ""
    color: Optional[str] = "#FFFFFF"

class AssignmentData(BaseModel):
    version: str = "1.0"
    video_id: str
    roster: List[RosterPlayer] = []
    assignments: Dict[str, str] = {}
    ignored_tracks: List[int] = []

class NewPlayerRequest(BaseModel):
    name: str
    jersey: Optional[str] = ""
    color: Optional[str] = "#FFFFFF"

# --- Helper Functions ---

def get_file_path(video_id: str) -> str:
    # Basic sanitization
    safe_name = os.path.basename(video_id)
    return os.path.join(DATA_DIR, f"{safe_name}_assignments.json")

def load_assignments(video_id: str) -> dict:
    path = get_file_path(video_id)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {
        "version": "1.0",
        "video_id": video_id,
        "roster": [],
        "assignments": {},
        "ignored_tracks": []
    }

def save_assignments(video_id: str, data: dict):
    path = get_file_path(video_id)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# --- API Endpoints ---

@app.get("/api/assignments/{video_id}", response_model=AssignmentData)
def get_video_assignments(video_id: str):
    """Fetch the assignment state for a specific video."""
    return load_assignments(video_id)

@app.post("/api/assignments/{video_id}")
def update_video_assignments(video_id: str, data: AssignmentData):
    """Overwrite the assignment state for a specific video."""
    # Convert Pydantic model back to dict for JSON saving
    save_assignments(video_id, data.dict())
    return {"status": "success", "message": f"Assignments saved for {video_id}"}

@app.post("/api/roster/{video_id}")
def add_roster_player(video_id: str, player: NewPlayerRequest):
    """Quickly add a new player to the roster."""
    data = load_assignments(video_id)
    
    # Generate a simple unique ID
    existing_ids = [p["id"] for p in data["roster"]]
    new_id = f"r_{len(existing_ids) + 1}"
    while new_id in existing_ids:
        new_id = f"r_{int(new_id.split('_')[1]) + 1}"
        
    new_player = {
        "id": new_id,
        "name": player.name,
        "jersey": player.jersey,
        "color": player.color
    }
    
    data["roster"].append(new_player)
    save_assignments(video_id, data)
    
    return {"status": "success", "player": new_player}

if __name__ == "__main__":
    import uvicorn
    # Run the server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
