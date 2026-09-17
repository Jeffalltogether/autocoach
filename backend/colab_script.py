import json
import cv2
import numpy as np
import torch
from scipy.signal import savgol_filter
from ultralytics import YOLO

# ==========================================
# 1. Smoothing & Filtering
# ==========================================

def smooth_track(data_array, window_length=15, polyorder=3):
    """Applies Savitzky-Golay filter to a 1D numpy array."""
    if len(data_array) < window_length:
        window_length = len(data_array)
        if window_length % 2 == 0:
            window_length -= 1
    
    if window_length <= polyorder:
        return data_array # Too short to smooth
        
    return savgol_filter(data_array, window_length, polyorder)

def main():
    input_json = "../data/processed/hockey_test_pose_tracking.json"
    output_json = "../data/processed/hockey_test_pose_tracking_smoothed.json"
    input_video = "../data/raw/hocky_test_video.mp4"
    output_video = "../data/processed/hockey_test_pose_output_smoothed.mp4"
    
    print(f"Loading raw tracking data from {input_json}...")
    with open(input_json, 'r') as f:
        frames_data = json.load(f)
        
    # 1. Reorganize data by player_id
    players = {}
    for frame_obj in frames_data:
        f_idx = frame_obj["frame"]
        for p in frame_obj["players"]:
            pid = p["id"]
            if pid not in players:
                players[pid] = {
                    "frames": [], "x": [], "y": [], "width": [], "height": [],
                    "keypoints": {i: {"x": [], "y": [], "conf": []} for i in range(17)}
                }
            
            players[pid]["frames"].append(f_idx)
            players[pid]["x"].append(p["x"])
            players[pid]["y"].append(p["y"])
            players[pid]["width"].append(p["width"])
            players[pid]["height"].append(p["height"])
            
            if "keypoints" in p:
                for i, kp in enumerate(p["keypoints"]):
                    players[pid]["keypoints"][i]["x"].append(kp["x"])
                    players[pid]["keypoints"][i]["y"].append(kp["y"])
                    players[pid]["keypoints"][i]["conf"].append(kp["conf"])
                    
    print(f"Extracted tracks for {len(players)} players. Applying Savitzky-Golay filter...")
    
    # 2. Interpolate missing frames and smooth
    for pid, data in players.items():
        min_f, max_f = min(data["frames"]), max(data["frames"])
        full_frames = np.arange(min_f, max_f + 1)
        
        # Interpolate and smooth bounding box
        data["full_frames"] = full_frames
        data["smooth_x"] = smooth_track(np.interp(full_frames, data["frames"], data["x"]))
        data["smooth_y"] = smooth_track(np.interp(full_frames, data["frames"], data["y"]))
        data["smooth_w"] = smooth_track(np.interp(full_frames, data["frames"], data["width"]))
        data["smooth_h"] = smooth_track(np.interp(full_frames, data["frames"], data["height"]))
        
        # Interpolate and smooth keypoints
        data["smooth_kpts"] = {}
        if len(data["keypoints"][0]["x"]) > 0:
            for i in range(17):
                kx = smooth_track(np.interp(full_frames, data["frames"], data["keypoints"][i]["x"]))
                ky = smooth_track(np.interp(full_frames, data["frames"], data["keypoints"][i]["y"]))
                kconf = np.interp(full_frames, data["frames"], data["keypoints"][i]["conf"])
                data["smooth_kpts"][i] = {"x": kx, "y": ky, "conf": kconf}
                
    # 3. Re-assemble into frame-by-frame JSON
    smoothed_frames = []
    max_total_frame = max(f["frame"] for f in frames_data)
    
    print("Re-assembling JSON...")
    for f_idx in range(max_total_frame + 1):
        frame_obj = {"frame": f_idx, "players": []}
        for pid, data in players.items():
            if f_idx in data["full_frames"]:
                idx = np.where(data["full_frames"] == f_idx)[0][0]
                player_obj = {
                    "id": pid,
                    "x": float(data["smooth_x"][idx]),
                    "y": float(data["smooth_y"][idx]),
                    "width": float(data["smooth_w"][idx]),
                    "height": float(data["smooth_h"][idx]),
                }
                if data["smooth_kpts"]:
                    kpts_list = []
                    for i in range(17):
                        kpts_list.append({
                            "x": float(data["smooth_kpts"][i]["x"][idx]),
                            "y": float(data["smooth_kpts"][i]["y"][idx]),
                            "conf": float(data["smooth_kpts"][i]["conf"][idx])
                        })
                    player_obj["keypoints"] = kpts_list
                frame_obj["players"].append(player_obj)
        smoothed_frames.append(frame_obj)
        
    with open(output_json, 'w') as f:
        json.dump(smoothed_frames, f, indent=2)
    print(f"Smoothed data saved to {output_json}")

    # 4. Generate visual overlay video
    print(f"Generating visual overlay video to {output_video}...")
    cap = cv2.VideoCapture(input_video)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))
    
    # Keypoint connection pairs for drawing the skeleton
    skeleton = [(15, 13), (13, 11), (16, 14), (14, 12), (11, 12), 
                (5, 11), (6, 12), (5, 6), (5, 7), (6, 8), (7, 9), 
                (8, 10), (1, 2), (0, 1), (0, 2), (1, 3), (2, 4), (3, 5), (4, 6)]

    for f_idx in range(max_total_frame + 1):
        success, frame = cap.read()
        if not success:
            break
            
        for player in smoothed_frames[f_idx]["players"]:
            # Draw bounding box
            x, y, w, h = player["x"], player["y"], player["width"], player["height"]
            x1, y1 = int(x - w/2), int(y - h/2)
            x2, y2 = int(x + w/2), int(y + h/2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"ID: {player['id']}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Draw skeleton
            if "keypoints" in player:
                kpts = player["keypoints"]
                for p1, p2 in skeleton:
                    if kpts[p1]["conf"] > 0.3 and kpts[p2]["conf"] > 0.3:
                        pt1 = (int(kpts[p1]["x"]), int(kpts[p1]["y"]))
                        pt2 = (int(kpts[p2]["x"]), int(kpts[p2]["y"]))
                        cv2.line(frame, pt1, pt2, (0, 255, 255), 2)
                for kp in kpts:
                    if kp["conf"] > 0.3:
                        cv2.circle(frame, (int(kp["x"]), int(kp["y"])), 3, (0, 0, 255), -1)

        out.write(frame)
        if f_idx % 100 == 0:
            print(f"Rendered {f_idx} frames...")

    cap.release()
    out.release()
    print("Video rendering complete!")

if __name__ == "__main__":
    main()

# ==========================================
# 2. Physics & Analytics
# ==========================================

def calculate_distance(pt1, pt2):
    return np.sqrt((pt2[0] - pt1[0])**2 + (pt2[1] - pt1[1])**2)

def apply_physics_and_events(frames_data, homography_matrix, fps):
    """
    Calculates real-world speed (MPH) and generates timeline events (Possession).
    Expects homography_matrix to be a 3x3 numpy array mapping pixels to feet.
    """
    timeline_events = []
    player_stats = {}
    
    # We need to track player history to calculate speed delta
    player_history = {}
    
    # Simple state tracking for events
    current_possessor = None
    
    for frame_obj in frames_data:
        f_idx = frame_obj["frame"]
        
        # --- 1. Project Pucks to Real-World Coordinates ---
        real_pucks = []
        for entity in frame_obj.get("entities", []):
            if "puck" in entity["type"]:
                pt = np.array([[[entity["x"], entity["y"]]]], dtype=np.float32)
                if homography_matrix is not None:
                    real_pt = cv2.perspectiveTransform(pt, homography_matrix)[0][0]
                    entity["real_x"] = float(real_pt[0])
                    entity["real_y"] = float(real_pt[1])
                    real_pucks.append(entity)

        # --- 2. Process Players (Velocity & Possession) ---
        frame_possessor = None
        
        for p in frame_obj["players"]:
            pid = p["id"]
            
            # Bottom-center of bounding box is where the skates are touching the ice
            skate_x = p["x"]
            skate_y = p["y"] + (p["height"] / 2.0)
            
            if homography_matrix is not None:
                pt = np.array([[[skate_x, skate_y]]], dtype=np.float32)
                real_pt = cv2.perspectiveTransform(pt, homography_matrix)[0][0]
                p["real_x"] = float(real_pt[0])
                p["real_y"] = float(real_pt[1])
            else:
                # Fallback to pixels if no homography is provided
                p["real_x"] = skate_x
                p["real_y"] = skate_y

            # Initialize stats dict
            if pid not in player_stats:
                player_stats[pid] = {
                    "max_velocity_mph": 0.0, 
                    "total_distance_ft": 0.0, 
                    "possession_frames": 0,
                    # New Youth Metrics
                    "speed_bursts": 0,
                    "active_frames": 0,
                    "total_frames_on_ice": 1,
                    "current_shift_start": f_idx,
                    "shifts": []
                }
            else:
                player_stats[pid]["total_frames_on_ice"] += 1

            # Calculate Velocity
            p["velocity_mph"] = 0.0
            if pid not in player_history:
                player_history[pid] = {
                    "last_real_x": p["real_x"], 
                    "last_real_y": p["real_y"], 
                    "last_frame": f_idx,
                    "in_burst": False
                }
            else:
                hist = player_history[pid]
                frames_passed = f_idx - hist["last_frame"]
                
                # Shift tracking: if they disappeared for > 3 seconds, count as a new shift
                if frames_passed > fps * 3.0:
                    shift_duration = hist["last_frame"] - player_stats[pid]["current_shift_start"]
                    if shift_duration > fps * 5.0: # Minimum 5 sec to record a shift
                        player_stats[pid]["shifts"].append({
                            "start_frame": player_stats[pid]["current_shift_start"],
                            "end_frame": hist["last_frame"],
                            "duration_sec": round(shift_duration / fps, 1)
                        })
                    player_stats[pid]["current_shift_start"] = f_idx
                
                if frames_passed > 0:
                    dist_ft = calculate_distance((p["real_x"], p["real_y"]), (hist["last_real_x"], hist["last_real_y"]))
                    
                    if homography_matrix is not None:
                        time_sec = frames_passed / fps
                        fps_speed = dist_ft / time_sec
                        mph = fps_speed * 0.681818
                        
                        p["velocity_mph"] = float(round(mph, 2))
                        player_stats[pid]["total_distance_ft"] += dist_ft
                        
                        if mph > player_stats[pid]["max_velocity_mph"]:
                            player_stats[pid]["max_velocity_mph"] = round(mph, 2)
                            
                        # The Energizer: Active ( > 3 mph) vs Gliding
                        if mph > 3.0:
                            player_stats[pid]["active_frames"] += frames_passed
                            
                        # True Acceleration Calculation (over a ~0.5 sec window)
                        recent_speeds = hist.setdefault("recent_speeds", [])
                        recent_speeds.append(mph)
                        
                        window_size = max(1, int(fps / 2))
                        if len(recent_speeds) > window_size:
                            old_mph = recent_speeds.pop(0)
                            accel_mph_s = (mph - old_mph) / (window_size / fps)
                        else:
                            accel_mph_s = 0.0
                            
                        # Speed Bursts: Explosive acceleration (e.g., accelerating > 6.0 mph/s)
                        # This rewards effort and quick starts regardless of the absolute top speed.
                        if accel_mph_s > 6.0 and not hist.get("in_burst", False):
                            player_stats[pid]["speed_bursts"] += 1
                            hist["in_burst"] = True
                        elif accel_mph_s < 1.0:
                            # Reset the burst trigger once acceleration normalizes
                            hist["in_burst"] = False
                            
                hist["last_real_x"] = p["real_x"]
                hist["last_real_y"] = p["real_y"]
                hist["last_frame"] = f_idx

            # Possession Heuristics
            p["has_puck"] = False
            if homography_matrix is not None and len(real_pucks) > 0:
                for puck in real_pucks:
                    # If we inferred stick blade, use it. Otherwise, use skates.
                    if "keypoints" in p:
                        # (We could hook up the infer_stick_vector here if we ported it, 
                        # but for now we'll just check distance to the player's general vicinity)
                        pass
                        
                    dist_to_puck = calculate_distance((p["real_x"], p["real_y"]), (puck["real_x"], puck["real_y"]))
                    
                    # If player is within 6 feet of the puck, consider it possession
                    if dist_to_puck < 6.0:
                        p["has_puck"] = True
                        player_stats[pid]["possession_frames"] += 1
                        frame_possessor = pid
                        break
                        
            # Contact Heuristics
            p["in_contact"] = False
            if homography_matrix is not None:
                for other_p in frame_obj["players"]:
                    if other_p["id"] != pid:
                        # Make sure other_p has real_x and real_y calculated already, 
                        # or just calculate inline to be safe if they haven't been processed yet
                        ox = other_p.get("real_x")
                        oy = other_p.get("real_y")
                        if ox is None or oy is None:
                            skate_x = other_p["x"]
                            skate_y = other_p["y"] + (other_p["height"] / 2.0)
                            pt = np.array([[[skate_x, skate_y]]], dtype=np.float32)
                            real_pt = cv2.perspectiveTransform(pt, homography_matrix)[0][0]
                            ox, oy = float(real_pt[0]), float(real_pt[1])
                            
                        dist_to_other = calculate_distance((p["real_x"], p["real_y"]), (ox, oy))
                        if dist_to_other < 3.0: # Within 3 feet
                            p["in_contact"] = True
                            break
                        
        # --- 3. Timeline Event Generation (Possession Changes) ---
        if homography_matrix is not None and frame_possessor != current_possessor and frame_possessor is not None:
                timeline_events.append({
                    "type": "possession_gained",
                    "frame": f_idx,
                    "player_id": frame_possessor
                })
                current_possessor = frame_possessor
                        
    # Finalize shifts and round off stats for clean JSON
    for pid, stats in player_stats.items():
        # Close out any pending shift at the end of the video
        if pid in player_history:
            hist = player_history[pid]
            shift_duration = hist["last_frame"] - stats["current_shift_start"]
            if shift_duration > fps * 5.0: # Minimum 5 sec to record a shift
                stats["shifts"].append({
                    "start_frame": stats["current_shift_start"],
                    "end_frame": hist["last_frame"],
                    "duration_sec": round(shift_duration / fps, 1)
                })

        stats["total_distance_ft"] = round(stats["total_distance_ft"], 2)
        stats["possession_time_sec"] = round(stats["possession_frames"] / fps, 2)
        stats["energizer_ratio"] = round(stats["active_frames"] / max(1, stats["total_frames_on_ice"]), 2)
        
        # Calculate normalized scores (0-100) for the frontend Radar chart
        # Assumptions for scaling: 3000ft is max hustle, 10 bursts is max speed, ratio is 0-1
        stats["radar_scores"] = {
            "hustle": min(100, int((stats["total_distance_ft"] / 3000.0) * 100)),
            "speed": min(100, int((stats["speed_bursts"] / 10.0) * 100)),
            "energizer": int(stats["energizer_ratio"] * 100)
        }
        
        # Cleanup internal tracking fields
        del stats["possession_frames"]
        del stats["current_shift_start"]
        del stats["active_frames"]
                        
    # Wrap everything in the new top-level structure
    final_output = {
        "metadata": {
            "fps": fps,
            "homography_matrix": homography_matrix.tolist() if homography_matrix is not None else None
        },
        "player_stats": player_stats,
        "timeline_events": timeline_events,
        "frames": frames_data
    }
    
    return final_output

# ==========================================
# 3. Main Extraction Pipeline
# ==========================================

def smooth_track(data_array, window_length=5, polyorder=2):
    """Applies Savitzky-Golay filter to a 1D numpy array."""
    if len(data_array) < window_length:
        window_length = len(data_array)
        if window_length % 2 == 0:
            window_length -= 1
    
    if window_length <= polyorder:
        return data_array
        
    return savgol_filter(data_array, window_length, polyorder)

def infer_stick_vector(keypoints):
    """
    Spike: Biomechanics (DP10-hockey-pose-estimation)
    Infers the hockey stick shaft and blade position based on the wrists.
    COCO Keypoints: 9 is Left Wrist, 10 is Right Wrist.
    """
    if len(keypoints) < 11:
        return None
        
    l_wrist = keypoints[9]
    r_wrist = keypoints[10]
    
    # Only infer if we have good confidence on both wrists
    if l_wrist["conf"] < 0.4 or r_wrist["conf"] < 0.4:
        return None
        
    # Determine top hand and bottom hand based on Y coordinate (lower Y is higher up on screen)
    if l_wrist["y"] < r_wrist["y"]:
        top_hand, bottom_hand = l_wrist, r_wrist
    else:
        top_hand, bottom_hand = r_wrist, l_wrist
        
    # Calculate the directional vector from top hand to bottom hand
    dx = bottom_hand["x"] - top_hand["x"]
    dy = bottom_hand["y"] - top_hand["y"]
    
    # Extend the vector to estimate the blade location on the ice
    # A standard hockey stick extends past the bottom hand by roughly 1.5x the distance between the hands
    extension_factor = 1.5
    blade_x = bottom_hand["x"] + (dx * extension_factor)
    blade_y = bottom_hand["y"] + (dy * extension_factor)
    
    return {
        "top_hand": {"x": top_hand["x"], "y": top_hand["y"]},
        "bottom_hand": {"x": bottom_hand["x"], "y": bottom_hand["y"]},
        "blade": {"x": blade_x, "y": blade_y}
    }

def smooth_tracking_data(frames_data):
    """Takes raw frame-by-frame tracking data and returns smoothed data."""
    players = {}
    for frame_obj in frames_data:
        f_idx = frame_obj["frame"]
        for p in frame_obj["players"]:
            pid = p["id"]
            if pid not in players:
                players[pid] = {
                    "frames": [], "x": [], "y": [], "width": [], "height": [],
                    "keypoints": {i: {"x": [], "y": [], "conf": []} for i in range(17)}
                }
            
            players[pid]["frames"].append(f_idx)
            players[pid]["x"].append(p["x"])
            players[pid]["y"].append(p["y"])
            players[pid]["width"].append(p["width"])
            players[pid]["height"].append(p["height"])
            
            if "keypoints" in p:
                for i, kp in enumerate(p["keypoints"]):
                    players[pid]["keypoints"][i]["x"].append(kp["x"])
                    players[pid]["keypoints"][i]["y"].append(kp["y"])
                    players[pid]["keypoints"][i]["conf"].append(kp["conf"])
            else:
                for i in range(17):
                    players[pid]["keypoints"][i]["x"].append(0.0)
                    players[pid]["keypoints"][i]["y"].append(0.0)
                    players[pid]["keypoints"][i]["conf"].append(0.0)
                    
    print(f"Extracted tracks for {len(players)} players. Applying filter...")
    for pid, data in players.items():
        min_f, max_f = min(data["frames"]), max(data["frames"])
        full_frames = np.arange(min_f, max_f + 1)
        
        data["full_frames"] = full_frames
        data["smooth_x"] = np.interp(full_frames, data["frames"], data["x"])
        data["smooth_y"] = np.interp(full_frames, data["frames"], data["y"])
        data["smooth_w"] = np.interp(full_frames, data["frames"], data["width"])
        data["smooth_h"] = np.interp(full_frames, data["frames"], data["height"])
        
        data["smooth_kpts"] = {}
        if len(data["keypoints"][0]["x"]) > 0:
            for i in range(17):
                x_arr = np.array(data["keypoints"][i]["x"])
                y_arr = np.array(data["keypoints"][i]["y"])
                conf_arr = np.array(data["keypoints"][i]["conf"])
                
                valid_mask = conf_arr > 0
                if np.sum(valid_mask) > 0:
                    valid_frames = np.array(data["frames"])[valid_mask]
                    valid_x = x_arr[valid_mask]
                    valid_y = y_arr[valid_mask]
                    
                    # Convert valid global coordinates into bounding-box-relative coordinates
                    # so that interpolated poses "stick" to the moving bounding box during gaps
                    smooth_x_valid = np.interp(valid_frames, full_frames, data["smooth_x"])
                    smooth_y_valid = np.interp(valid_frames, full_frames, data["smooth_y"])
                    smooth_w_valid = np.interp(valid_frames, full_frames, data["smooth_w"])
                    smooth_h_valid = np.interp(valid_frames, full_frames, data["smooth_h"])
                    
                    # Prevent division by zero
                    smooth_w_valid[smooth_w_valid == 0] = 1.0
                    smooth_h_valid[smooth_h_valid == 0] = 1.0
                    
                    rel_x = (valid_x - smooth_x_valid) / smooth_w_valid
                    rel_y = (valid_y - smooth_y_valid) / smooth_h_valid
                    
                    # Interpolate relative positions across the gap
                    interp_rel_x = np.interp(full_frames, valid_frames, rel_x)
                    interp_rel_y = np.interp(full_frames, valid_frames, rel_y)
                    
                    # Convert back to global coordinates using the bounding box path
                    kx = interp_rel_x * data["smooth_w"] + data["smooth_x"]
                    ky = interp_rel_y * data["smooth_h"] + data["smooth_y"]
                    
                    # Interpolate confidence ONLY across gaps, dropping it at start/end
                    kconf = np.interp(full_frames, valid_frames, conf_arr[valid_mask], left=0.0, right=0.0)
                    
                    kx = smooth_track(kx)
                    ky = smooth_track(ky)
                    
                    # Force X, Y to exactly 0.0 where confidence is practically 0 to prevent "darting angels" 
                    # from being drawn returning to the top left of the screen (0,0). Because we used left/right=0.0 above,
                    # this effectively trims the head/tail extrapolation without affecting intra-track gaps!
                    kx[kconf < 0.1] = 0.0
                    ky[kconf < 0.1] = 0.0
                else:
                    kx = np.zeros_like(full_frames, dtype=float)
                    ky = np.zeros_like(full_frames, dtype=float)
                    kconf = np.zeros_like(full_frames, dtype=float)

                data["smooth_kpts"][i] = {"x": kx, "y": ky, "conf": kconf}

    # Extract original entities to preserve them across the rebuild
    original_entities = {}
    for f in frames_data:
        original_entities[f["frame"]] = f.get("entities", [])
                
    smoothed_frames = []
    max_total_frame = max(f["frame"] for f in frames_data)
    
    for f_idx in range(max_total_frame + 1):
        frame_obj = {"frame": f_idx, "players": [], "entities": original_entities.get(f_idx, [])}
        for pid, data in players.items():
            if f_idx in data["full_frames"]:
                idx = np.where(data["full_frames"] == f_idx)[0][0]
                player_obj = {
                    "id": pid,
                    "x": float(data["smooth_x"][idx]),
                    "y": float(data["smooth_y"][idx]),
                    "width": float(data["smooth_w"][idx]),
                    "height": float(data["smooth_h"][idx]),
                }
                if data["smooth_kpts"]:
                    kpts_list = []
                    for i in range(17):
                        kpts_list.append({
                            "x": float(data["smooth_kpts"][i]["x"][idx]),
                            "y": float(data["smooth_kpts"][i]["y"][idx]),
                            "conf": float(data["smooth_kpts"][i]["conf"][idx])
                        })
                    player_obj["keypoints"] = kpts_list
                frame_obj["players"].append(player_obj)
        smoothed_frames.append(frame_obj)
        
    return smoothed_frames

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
    print(f"Loading YOLO models on device: {device}...")
    
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
        
    print(f"Pipeline complete! Saved to {out_json_path}")

# run_pipeline(VIDEO_PATH, OUTPUT_JSON_PATH, MAX_FRAMES)
