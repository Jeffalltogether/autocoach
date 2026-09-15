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
                x_arr = np.array(data["keypoints"][i]["x"])
                y_arr = np.array(data["keypoints"][i]["y"])
                conf_arr = np.array(data["keypoints"][i]["conf"])
                
                valid_mask = conf_arr > 0
                if np.sum(valid_mask) > 0:
                    valid_frames = np.array(data["frames"])[valid_mask]
                    valid_x = x_arr[valid_mask]
                    valid_y = y_arr[valid_mask]
                    
                    # Interpolate positions ONLY using frames where the keypoint was actually detected
                    kx = np.interp(full_frames, valid_frames, valid_x)
                    ky = np.interp(full_frames, valid_frames, valid_y)
                    # Interpolate confidence across all frames so it naturally fades out when missing
                    kconf = np.interp(full_frames, data["frames"], conf_arr)
                    
                    kx = smooth_track(kx)
                    ky = smooth_track(ky)
                    
                    # Force X, Y to exactly 0.0 where confidence is practically 0 to prevent "darting angels" 
                    # from being drawn returning to the top left of the screen (0,0)
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
    
    drive_model_dir = "/content/drive/MyDrive/autocoach/models"
    
    # We use 6 independent trackers for the 3x2 SAHI grid to maintain tracking history per zone
    tracker_path = f"{drive_model_dir}/yolov8x.pt" if device == 'cuda' else "yolov8n.pt"
    trackers = {
        "TL": YOLO(tracker_path), "TC": YOLO(tracker_path), "TR": YOLO(tracker_path),
        "BL": YOLO(tracker_path), "BC": YOLO(tracker_path), "BR": YOLO(tracker_path)
    }
    
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
    
    # Global tracking maps for NMS merging
    local_to_global = {}
    next_global_id = 1
    
    def calculate_iou(boxA, boxB):
        xA, yA = max(boxA[0], boxB[0]), max(boxA[1], boxB[1])
        xB, yB = min(boxA[2], boxB[2]), min(boxA[3], boxB[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        if interArea == 0: return 0.0
        return interArea / float(((boxA[2]-boxA[0])*(boxA[3]-boxA[1])) + ((boxB[2]-boxB[0])*(boxB[3]-boxB[1])) - interArea)
    
    print("STEP 1: Running SAHI Tiled Tracking & Pose extraction...", flush=True)
    while cap.isOpened():
        success, frame = cap.read()
        if not success or (args.frames and frame_idx >= args.frames):
            break
            
        H, W = frame.shape[:2]
        # Dynamically slice the extremely wide panorama into a 3x2 grid with overlaps
        overlap_w = 300
        overlap_h = 200
        zone_w = W // 3
        zone_h = H // 2
        zones = [
            {"name": "TL", "x1": 0, "x2": zone_w + overlap_w, "y1": 0, "y2": zone_h + overlap_h},
            {"name": "TC", "x1": zone_w - overlap_w, "x2": 2 * zone_w + overlap_w, "y1": 0, "y2": zone_h + overlap_h},
            {"name": "TR", "x1": 2 * zone_w - overlap_w, "x2": W, "y1": 0, "y2": zone_h + overlap_h},
            {"name": "BL", "x1": 0, "x2": zone_w + overlap_w, "y1": zone_h - overlap_h, "y2": H},
            {"name": "BC", "x1": zone_w - overlap_w, "x2": 2 * zone_w + overlap_w, "y1": zone_h - overlap_h, "y2": H},
            {"name": "BR", "x1": 2 * zone_w - overlap_w, "x2": W, "y1": zone_h - overlap_h, "y2": H}
        ]

        # 1. Run Tracker Model on each zone independently
        all_boxes = []
        for z in zones:
            crop_zone = frame[z["y1"]:z["y2"], z["x1"]:z["x2"]]
            # We process at a lower imgsz (1280) since the width is already cut in third. This is blazingly fast.
            res = trackers[z["name"]].track(crop_zone, persist=True, classes=[0], verbose=False, device=device, imgsz=1280)
            
            if res[0].boxes is not None and res[0].boxes.id is not None:
                boxes = res[0].boxes.xyxy.cpu().numpy()
                ids = res[0].boxes.id.int().cpu().tolist()
                confs = res[0].boxes.conf.cpu().tolist()
                
                for b, t_id, conf in zip(boxes, ids, confs):
                    gx1, gy1, gx2, gy2 = b[0] + z["x1"], b[1] + z["y1"], b[2] + z["x1"], b[3] + z["y1"]
                    
                    # EARLY FILTERING: Check ROI immediately to prevent $O(N^2)$ NMS explosion on crowded stands
                    if roi_polygon is not None:
                        skates_pt = (int((gx1 + gx2) / 2.0), int(gy2)) # Bottom center of the bounding box
                        if cv2.pointPolygonTest(roi_polygon, skates_pt, False) < 0:
                            continue # Skip appending this box; it's outside the ROI
                            
                    local_id = f"{z['name']}_{t_id}"
                    all_boxes.append({
                        "local_id": local_id,
                        "box": [gx1, gy1, gx2, gy2],
                        "conf": conf
                    })
                    
        # 2. NMS Merge Tracked Boxes across zones
        merged_players = []
        used = set()
        all_boxes = sorted(all_boxes, key=lambda x: x["conf"], reverse=True)
        
        for i, boxA in enumerate(all_boxes):
            if i in used: continue
            cluster = [boxA]
            used.add(i)
            
            for j in range(i + 1, len(all_boxes)):
                if j in used: continue
                if calculate_iou(boxA["box"], all_boxes[j]["box"]) > 0.4:
                    cluster.append(all_boxes[j])
                    used.add(j)
                    
            assigned_global_id = None
            for b in cluster:
                if b["local_id"] in local_to_global:
                    assigned_global_id = local_to_global[b["local_id"]]
                    break
                    
            if assigned_global_id is None:
                assigned_global_id = next_global_id
                next_global_id += 1
                
            for b in cluster:
                local_to_global[b["local_id"]] = assigned_global_id
                
            # Average the boxes in the cluster
            avg_x1 = sum(b["box"][0] for b in cluster) / len(cluster)
            avg_y1 = sum(b["box"][1] for b in cluster) / len(cluster)
            avg_x2 = sum(b["box"][2] for b in cluster) / len(cluster)
            avg_y2 = sum(b["box"][3] for b in cluster) / len(cluster)
            
            w, h = avg_x2 - avg_x1, avg_y2 - avg_y1
            # FIX: Convert Top-Left back to Center X, Y for YOLO/Frontend expectations
            center_x = avg_x1 + w / 2.0
            center_y = avg_y1 + h / 2.0
            
            merged_players.append({
                "id": assigned_global_id, "role": "player",
                "x": center_x, "y": center_y, "width": w, "height": h,
                "xyxy": [avg_x1, avg_y1, avg_x2, avg_y2]
            })

        # 3. Run Hockey Model (for pucks, goalies, referees, etc.)
        hockey_results = hockey_model(frame, verbose=False, device=device, imgsz=2560)
        
        frame_data = {"frame": frame_idx, "players": [], "entities": []}
        
        # 4. Filter merged players by ROI and Batched Pose Extraction
        valid_players = []
        crops = []
        offsets = []
        
        for p in merged_players:
            # Define crop boundaries (with a 10px margin)
            x1, y1, x2, y2 = [int(v) for v in p["xyxy"]]
            cy1, cy2 = max(0, y1-10), min(frame.shape[0], y2+10)
            cx1, cx2 = max(0, x1-10), min(frame.shape[1], x2+10)
            
            crop = frame[cy1:cy2, cx1:cx2]
            if crop.size > 0:
                crops.append(crop)
                offsets.append((cx1, cy1))
                valid_players.append(p)

            # Run Pose Model in a single batched inference
            if len(crops) > 0:
                # Add a safe batch size limit to prevent CUDA OOM on massive crowded frames
                BATCH_SIZE = 32
                for b_idx in range(0, len(crops), BATCH_SIZE):
                    batch_crops = crops[b_idx:b_idx+BATCH_SIZE]
                    pose_results = pose_model(batch_crops, verbose=False, device=device)
                    
                    for i, res in enumerate(pose_results):
                        global_i = b_idx + i
                        player_dict = valid_players[global_i]
                        offset_x, offset_y = offsets[global_i]
                        
                        if res.keypoints is not None and len(res.keypoints) > 0:
                            kpts = res.keypoints.data[0].cpu().numpy()
                            kpts_list = []
                            for kx, ky, conf in kpts:
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
                    if "player" not in entity_name:
                        frame_data["entities"].append({
                            "type": entity_name,
                            "x": x, "y": y, "width": w, "height": h, "conf": conf
                        })
        
        tracking_data.append(frame_data)
        frame_idx += 1
        
        # Print frequently to keep Colab CLI WebSocket alive (prevents TimeoutError)
        if frame_idx % 5 == 0:
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
