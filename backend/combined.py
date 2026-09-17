import json

import cv2
import numpy as np
from scipy.signal import savgol_filter


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
import cv2
import numpy as np


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
                player_stats[pid] = {"max_velocity_mph": 0.0, "total_distance_ft": 0.0, "possession_frames": 0}

            # Calculate Velocity
            p["velocity_mph"] = 0.0
            if pid not in player_history:
                player_history[pid] = {"last_real_x": p["real_x"], "last_real_y": p["real_y"], "last_frame": f_idx}
            else:
                hist = player_history[pid]
                frames_passed = f_idx - hist["last_frame"]
                
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
                        
    # Round off the stats for clean JSON
    for pid, stats in player_stats.items():
        stats["total_distance_ft"] = round(stats["total_distance_ft"], 2)
        stats["possession_time_sec"] = round(stats["possession_frames"] / fps, 2)
        del stats["possession_frames"]
                        
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
import json

import cv2
import numpy as np
from scipy.signal import savgol_filter
from ultralytics import YOLO


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
                kx = smooth_track(np.interp(full_frames, data["frames"], data["keypoints"][i]["x"]))
                ky = smooth_track(np.interp(full_frames, data["frames"], data["keypoints"][i]["y"]))
                kconf = np.interp(full_frames, data["frames"], data["keypoints"][i]["conf"])
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

import argparse


def main():
    parser = argparse.ArgumentParser(description="Autocoach Dual-Model Pipeline")
    parser.add_argument("--video", type=str, required=True, help="Path to input video file")
    parser.add_argument("--out_json", type=str, required=True, help="Path to output JSON file")
    parser.add_argument("--frames", type=int, default=None, help="Max frames to process (for testing)")
    parser.add_argument("--homography", type=str, default=None, help="Path to homography.json")
    parser.add_argument("--roi", type=str, default=None, help="Path to ROI polygon JSON")
    args = parser.parse_args()
    
    import os

    import torch

    from physics import apply_physics_and_events
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    roi_polygon = None
    if args.roi and os.path.exists(args.roi):
        with open(args.roi, 'r') as f:
            roi_data = json.load(f)
            roi_polygon = np.array(roi_data["roi_polygon"], dtype=np.int32)
            print(f"Loaded ROI polygon from {args.roi}")

    # Load Homography (if provided)
    H_matrix = None
    if args.homography and os.path.exists(args.homography):
        with open(args.homography, "r") as f:
            homog_data = json.load(f)
            H_matrix = np.array(homog_data["homography_matrix"], dtype=np.float32)
            print(f"Loaded homography matrix from {args.homography}")
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Loading YOLO models (Pose + Custom HockeyAI) on device: {device}...", flush=True)
    
    # Point both models to the persistent Google Drive folder on Colab to prevent re-downloading
    drive_model_dir = "/content/drive/MyDrive/autocoach/models"
    
    pose_path = f"{drive_model_dir}/yolov8n-pose.pt" if device == 'cuda' else "yolov8n-pose.pt"
    hockey_path = f"{drive_model_dir}/HockeyAI_model_weight.pt" if device == 'cuda' else "HockeyAI_model_weight.pt"
    
    pose_model = YOLO(pose_path) 
    hockey_model = YOLO(hockey_path)
    
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"Error opening video file: {args.video}")
        return
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    tracking_data = []
    frame_idx = 0
    
    print("STEP 1: Running dual-model tracking extraction...", flush=True)
    while cap.isOpened():
        success, frame = cap.read()
        if not success or (args.frames and frame_idx >= args.frames):
            break

        # 1. Run Pose Model (for players & skeletons) at High-Res to catch tiny players in the corners
        pose_results = pose_model.track(frame, persist=True, classes=[0], verbose=False, device=device, imgsz=2560)
        
        # 2. Run Hockey Model (for pucks, goalies, referees, etc.)
        hockey_results = hockey_model(frame, verbose=False, device=device, imgsz=2560)
        
        frame_data = {"frame": frame_idx, "players": [], "entities": []}
        
        # Extract Players (Pose)
        if pose_results[0].boxes is not None and pose_results[0].boxes.id is not None:
            boxes = pose_results[0].boxes.xywh.cpu().numpy()
            track_ids = pose_results[0].boxes.id.int().cpu().tolist()
            
            has_keypoints = pose_results[0].keypoints is not None
            if has_keypoints:
                keypoints_batch = pose_results[0].keypoints.data.cpu().numpy()
            
            for i, (box, track_id) in enumerate(zip(boxes, track_ids)):
                x, y, w, h = [float(v) for v in box]
                
                # Check ROI using the bottom-center of the bounding box (the skates)
                if roi_polygon is not None:
                    skates_pt = (int(x), int(y + (h / 2.0)))
                    # pointPolygonTest returns >= 0 if the point is inside or on the contour
                    if cv2.pointPolygonTest(roi_polygon, skates_pt, False) < 0:
                        continue # Skip this player, they are outside the ROI
                
                player_dict = {"id": track_id, "role": "player", "x": x, "y": y, "width": w, "height": h}
                
                if has_keypoints and i < len(keypoints_batch):
                    kpts_list = []
                    for kpt in keypoints_batch[i]:
                        kx, ky, conf = [float(v) for v in kpt]
                        kpts_list.append({"x": kx, "y": ky, "conf": conf})
                    player_dict["keypoints"] = kpts_list

                frame_data["players"].append(player_dict)
                
        # Extract Custom Entities (Hockey Model)
        if hockey_results[0].boxes is not None:
            boxes = hockey_results[0].boxes.xywh.cpu().numpy()
            classes = hockey_results[0].boxes.cls.int().cpu().tolist()
            confs = hockey_results[0].boxes.conf.cpu().tolist()
            class_names = hockey_results[0].names
            
            for box, cls, conf in zip(boxes, classes, confs):
                if conf > 0.3: # Basic confidence threshold
                    x, y, w, h = [float(v) for v in box]
                    
                    # Check ROI using bottom-center
                    if roi_polygon is not None:
                        pt = (int(x), int(y + (h / 2.0)))
                        if cv2.pointPolygonTest(roi_polygon, pt, False) < 0:
                            continue
                            
                    entity_name = class_names[cls].lower()
                    # We skip standard players since the pose model handles them better,
                    # but we keep pucks, goalies, referees, etc.
                    if "player" not in entity_name:
                        frame_data["entities"].append({
                            "type": entity_name,
                            "x": x, "y": y, "width": w, "height": h, "conf": conf
                        })
        
        tracking_data.append(frame_data)
        frame_idx += 1
        if frame_idx % 30 == 0:
            print(f"Extracted {frame_idx} frames...", flush=True)

    cap.release()
    
    print("STEP 2: Applying Savitzky-Golay smoothing...", flush=True)
    smoothed_data = smooth_tracking_data(tracking_data)
    
    print("STEP 3: Applying Physics & Generating Analytics...", flush=True)
    final_data = apply_physics_and_events(smoothed_data, H_matrix, fps)
    
    with open(args.out_json, "w") as f:
        json.dump(final_data, f, indent=2)
    print(f"Final JSON with analytics saved to {args.out_json}", flush=True)
    
    print("Pipeline complete! (Video rendering skipped for performance)", flush=True)

if __name__ == "__main__":
    main()
