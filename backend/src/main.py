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
    
    tracker_path = f"{drive_model_dir}/yolov8n.pt" if device == 'cuda' else "yolov8n.pt"
    pose_path = f"{drive_model_dir}/yolov8n-pose.pt" if device == 'cuda' else "yolov8n-pose.pt"
    hockey_path = f"{drive_model_dir}/HockeyAI_model_weight.pt" if device == 'cuda' else "HockeyAI_model_weight.pt"
    
    # Top-Down Architecture: Tracker finds boxes, Pose finds skeletons inside boxes
    tracker_model = YOLO(tracker_path)
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

        # 1. Run Tracker Model (for robust tiny bounding boxes)
        track_results = tracker_model.track(frame, persist=True, classes=[0], verbose=False, device=device, imgsz=2560)
        
        # 2. Run Hockey Model (for pucks, goalies, referees, etc.)
        hockey_results = hockey_model(frame, verbose=False, device=device, imgsz=2560)
        
        frame_data = {"frame": frame_idx, "players": [], "entities": []}
        
        # Extract Players (Top-Down Tracker -> Batched Pose Crops)
        if track_results[0].boxes is not None and track_results[0].boxes.id is not None:
            # We need xyxy for cropping and xywh for saving
            boxes_xyxy = track_results[0].boxes.xyxy.cpu().numpy()
            boxes_xywh = track_results[0].boxes.xywh.cpu().numpy()
            track_ids = track_results[0].boxes.id.int().cpu().tolist()
            
            # Filter by ROI and collect valid crops
            valid_players = []
            crops = []
            offsets = []
            
            for box_xyxy, box_xywh, track_id in zip(boxes_xyxy, boxes_xywh, track_ids):
                x, y, w, h = [float(v) for v in box_xywh]
                
                # Check ROI using the bottom-center of the bounding box (the skates)
                if roi_polygon is not None:
                    skates_pt = (int(x), int(y + (h / 2.0)))
                    if cv2.pointPolygonTest(roi_polygon, skates_pt, False) < 0:
                        continue # Skip this player, they are outside the ROI
                        
                # Define crop boundaries (with a 10px margin)
                x1, y1, x2, y2 = [int(v) for v in box_xyxy]
                cy1, cy2 = max(0, y1-10), min(frame.shape[0], y2+10)
                cx1, cx2 = max(0, x1-10), min(frame.shape[1], x2+10)
                
                crop = frame[cy1:cy2, cx1:cx2]
                if crop.size > 0:
                    crops.append(crop)
                    offsets.append((cx1, cy1))
                    valid_players.append({"id": track_id, "role": "player", "x": x, "y": y, "width": w, "height": h})

            # Run Pose Model in a single batched inference
            if len(crops) > 0:
                pose_results = pose_model(crops, verbose=False, device=device)
                
                for i, res in enumerate(pose_results):
                    player_dict = valid_players[i]
                    offset_x, offset_y = offsets[i]
                    
                    if res.keypoints is not None and len(res.keypoints) > 0:
                        kpts = res.keypoints.data[0].cpu().numpy()
                        kpts_list = []
                        for kx, ky, conf in kpts:
                            # If conf is 0, the model didn't detect the keypoint, leave it at 0,0
                            if conf > 0:
                                kpts_list.append({"x": float(kx) + offset_x, "y": float(ky) + offset_y, "conf": float(conf)})
                            else:
                                kpts_list.append({"x": 0.0, "y": 0.0, "conf": 0.0})
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
