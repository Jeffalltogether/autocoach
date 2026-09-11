import cv2
import json
import numpy as np
from ultralytics import YOLO
from scipy.signal import savgol_filter

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
                    
    print(f"Extracted tracks for {len(players)} players. Applying filter...")
    for pid, data in players.items():
        min_f, max_f = min(data["frames"]), max(data["frames"])
        full_frames = np.arange(min_f, max_f + 1)
        
        data["full_frames"] = full_frames
        data["smooth_x"] = smooth_track(np.interp(full_frames, data["frames"], data["x"]))
        data["smooth_y"] = smooth_track(np.interp(full_frames, data["frames"], data["y"]))
        data["smooth_w"] = smooth_track(np.interp(full_frames, data["frames"], data["width"]))
        data["smooth_h"] = smooth_track(np.interp(full_frames, data["frames"], data["height"]))
        
        data["smooth_kpts"] = {}
        if len(data["keypoints"][0]["x"]) > 0:
            for i in range(17):
                kx = smooth_track(np.interp(full_frames, data["frames"], data["keypoints"][i]["x"]))
                ky = smooth_track(np.interp(full_frames, data["frames"], data["keypoints"][i]["y"]))
                kconf = np.interp(full_frames, data["frames"], data["keypoints"][i]["conf"])
                data["smooth_kpts"][i] = {"x": kx, "y": ky, "conf": kconf}
                
    smoothed_frames = []
    max_total_frame = max(f["frame"] for f in frames_data)
    
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
        
    return smoothed_frames

import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Autocoach Dual-Model Pipeline")
    parser.add_argument("--video", type=str, default="../data/raw/pro_game.mp4", help="Path to input video")
    parser.add_argument("--out_json", type=str, default="../data/processed/hockey_tracking_final.json")
    parser.add_argument("--out_video", type=str, default="../data/processed/hockey_tracking_final.mp4")
    parser.add_argument("--frames", type=int, default=None, help="Max frames to process (for testing)")
    args = parser.parse_args()
    
    print("Loading YOLO models (Pose + Custom HockeyAI)...", flush=True)
    pose_model = YOLO("yolov8n-pose.pt") 
    hockey_model = YOLO("HockeyAI_model_weight.pt")
    
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"Error opening video file: {args.video}")
        return
        
    tracking_data = []
    frame_idx = 0
    
    print("STEP 1: Running dual-model tracking extraction...", flush=True)
    while cap.isOpened():
        success, frame = cap.read()
        if not success or (args.frames and frame_idx >= args.frames):
            break

        # 1. Run Pose Model (for players & skeletons)
        pose_results = pose_model.track(frame, persist=True, classes=[0], verbose=False, device='cpu')
        
        # 2. Run Hockey Model (for pucks, goalies, referees, etc.)
        hockey_results = hockey_model(frame, verbose=False, device='cpu')
        
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
        if frame_idx % 100 == 0:
            print(f"Extracted {frame_idx} frames...", flush=True)

    cap.release()
    
    print("STEP 2: Applying Savitzky-Golay smoothing...", flush=True)
    smoothed_data = smooth_tracking_data(tracking_data)
    
    with open(args.out_json, "w") as f:
        json.dump(smoothed_data, f, indent=2)
    print(f"Smoothed JSON saved to {args.out_json}", flush=True)
    
    print("STEP 3: Rendering final smoothed video...", flush=True)
    cap = cv2.VideoCapture(args.video)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(args.out_video, fourcc, fps, (width, height))
    
    skeleton = [(15, 13), (13, 11), (16, 14), (14, 12), (11, 12), 
                (5, 11), (6, 12), (5, 6), (5, 7), (6, 8), (7, 9), 
                (8, 10), (1, 2), (0, 1), (0, 2), (1, 3), (2, 4), (3, 5), (4, 6)]

    max_frames = len(smoothed_data)
    for f_idx in range(max_frames):
        success, frame = cap.read()
        if not success:
            break
            
        # Draw Players
        for player in smoothed_data[f_idx]["players"]:
            x, y, w, h = player["x"], player["y"], player["width"], player["height"]
            x1, y1 = int(x - w/2), int(y - h/2)
            x2, y2 = int(x + w/2), int(y + h/2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"ID: {player['id']}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
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
                        
                stick = infer_stick_vector(kpts)
                if stick:
                    pt_top = (int(stick["top_hand"]["x"]), int(stick["top_hand"]["y"]))
                    pt_blade = (int(stick["blade"]["x"]), int(stick["blade"]["y"]))
                    cv2.line(frame, pt_top, pt_blade, (255, 255, 255), 3)
                    cv2.circle(frame, pt_blade, 6, (0, 0, 0), -1)

        # Draw Custom Entities (Pucks, Goalies, Refs)
        if "entities" in smoothed_data[f_idx]:
            for entity in smoothed_data[f_idx]["entities"]:
                x, y, w, h = entity["x"], entity["y"], entity["width"], entity["height"]
                x1, y1 = int(x - w/2), int(y - h/2)
                x2, y2 = int(x + w/2), int(y + h/2)
                
                # Different colors for different entities
                color = (0, 0, 255) # Red for puck by default
                if "goal" in entity["type"]: color = (255, 0, 0)
                elif "ref" in entity["type"]: color = (0, 165, 255)
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                cv2.putText(frame, entity["type"], (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        out.write(frame)
        if f_idx % 100 == 0:
            print(f"Rendered {f_idx} frames...", flush=True)

    cap.release()
    out.release()
    print("Pipeline complete!", flush=True)

if __name__ == "__main__":
    main()
