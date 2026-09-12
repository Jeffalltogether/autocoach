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
