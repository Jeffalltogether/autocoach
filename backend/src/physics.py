import cv2
import numpy as np
from scipy.signal import savgol_filter

def calculate_distance(pt1, pt2):
    return np.sqrt((pt2[0] - pt1[0])**2 + (pt2[1] - pt1[1])**2)

def smooth_array(arr, window_length=15, polyorder=3):
    if len(arr) < window_length:
        if len(arr) <= polyorder:
            return arr
        wl = len(arr) if len(arr) % 2 != 0 else len(arr) - 1
        return savgol_filter(arr, wl, polyorder)
    return savgol_filter(arr, window_length, polyorder)

def apply_physics_and_events(frames_data, homography_matrix, fps):
    """
    Calculates real-world speed (MPH) and generates timeline events (Possession).
    Expects homography_matrix to be a 3x3 numpy array mapping pixels to feet.
    """
    timeline_events = []
    player_stats = {}
    
    # --- Pass 1: Extract Real Coordinates ---
    for f_idx, frame_obj in enumerate(frames_data):
        # 1. Pucks
        for entity in frame_obj.get("entities", []):
            if "puck" in entity["type"]:
                if homography_matrix is not None:
                    pt = np.array([[[entity["x"], entity["y"]]]], dtype=np.float32)
                    real_pt = cv2.perspectiveTransform(pt, homography_matrix)[0][0]
                    entity["real_x"] = float(real_pt[0])
                    entity["real_y"] = float(real_pt[1])
                else:
                    entity["real_x"] = float(entity["x"])
                    entity["real_y"] = float(entity["y"])
                    
        # 2. Players
        for p in frame_obj.get("players", []):
            skate_x = p["x"]
            skate_y = p["y"] + (p["height"] / 2.0)
            if homography_matrix is not None:
                pt = np.array([[[skate_x, skate_y]]], dtype=np.float32)
                real_pt = cv2.perspectiveTransform(pt, homography_matrix)[0][0]
                p["real_x"] = float(real_pt[0])
                p["real_y"] = float(real_pt[1])
            else:
                p["real_x"] = float(skate_x)
                p["real_y"] = float(skate_y)

    # --- Pass 2: Smooth Coordinates and Calculate Velocities ---
    player_tracks = {}
    for f_idx, frame_obj in enumerate(frames_data):
        for p in frame_obj.get("players", []):
            pid = p["id"]
            if pid not in player_tracks:
                player_tracks[pid] = {"frames": [], "rx": [], "ry": [], "refs": []}
            player_tracks[pid]["frames"].append(f_idx)
            player_tracks[pid]["rx"].append(p["real_x"])
            player_tracks[pid]["ry"].append(p["real_y"])
            player_tracks[pid]["refs"].append(p)
            
    # Window size: roughly 0.5 seconds, must be odd
    window_len = max(5, int(fps / 2))
    if window_len % 2 == 0:
        window_len += 1
        
    for pid, track in player_tracks.items():
        frames = track["frames"]
        rx = np.array(track["rx"])
        ry = np.array(track["ry"])
        
        # Smooth real coordinates to eliminate tracking jitter
        smooth_rx = smooth_array(rx, window_length=window_len, polyorder=2)
        smooth_ry = smooth_array(ry, window_length=window_len, polyorder=2)
        
        # Calculate raw mph from the smoothed coordinates
        raw_mph = np.zeros(len(frames))
        for i in range(1, len(frames)):
            frames_passed = frames[i] - frames[i-1]
            if frames_passed > 0 and homography_matrix is not None:
                dist_ft = calculate_distance((smooth_rx[i], smooth_ry[i]), (smooth_rx[i-1], smooth_ry[i-1]))
                time_sec = frames_passed / fps
                raw_mph[i] = (dist_ft / time_sec) * 0.681818
                
        # Smooth the velocities to eliminate derivative spikes
        smooth_mph = smooth_array(raw_mph, window_length=window_len, polyorder=2)
        smooth_mph = np.clip(smooth_mph, 0.0, None)
        
        # Write back smoothed values
        for i, p in enumerate(track["refs"]):
            p["real_x"] = float(smooth_rx[i])
            p["real_y"] = float(smooth_ry[i])
            p["velocity_mph"] = float(round(smooth_mph[i], 2))


    # --- Pass 3: Process Stats and Events (Using Smoothed Data) ---
    player_history = {}
    current_possessor = None
    
    for f_idx, frame_obj in enumerate(frames_data):
        real_pucks = [e for e in frame_obj.get("entities", []) if "puck" in e["type"] and "real_x" in e]
        frame_possessor = None
        
        for p in frame_obj.get("players", []):
            pid = p["id"]
            
            # Initialize stats dict
            if pid not in player_stats:
                player_stats[pid] = {
                    "max_velocity_mph": 0.0, 
                    "total_distance_ft": 0.0, 
                    "possession_frames": 0,
                    "speed_bursts": 0,
                    "active_frames": 0,
                    "total_frames_on_ice": 1,
                    "current_shift_start": f_idx,
                    "shifts": []
                }
            else:
                player_stats[pid]["total_frames_on_ice"] += 1
                
            mph = p.get("velocity_mph", 0.0)

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
                    if shift_duration > fps * 5.0:
                        player_stats[pid]["shifts"].append({
                            "start_frame": player_stats[pid]["current_shift_start"],
                            "end_frame": hist["last_frame"],
                            "duration_sec": round(shift_duration / fps, 1)
                        })
                    player_stats[pid]["current_shift_start"] = f_idx
                
                if frames_passed > 0:
                    dist_ft = calculate_distance((p["real_x"], p["real_y"]), (hist["last_real_x"], hist["last_real_y"]))
                    
                    if homography_matrix is not None:
                        player_stats[pid]["total_distance_ft"] += dist_ft
                        
                        if mph > player_stats[pid]["max_velocity_mph"]:
                            player_stats[pid]["max_velocity_mph"] = round(mph, 2)
                            
                        # Active vs Gliding
                        if mph > 3.0:
                            player_stats[pid]["active_frames"] += frames_passed
                            
                        # Acceleration Calculation (from already smoothed velocity)
                        recent_speeds = hist.setdefault("recent_speeds", [])
                        recent_speeds.append(mph)
                        
                        window_size = max(1, int(fps / 2))
                        if len(recent_speeds) > window_size:
                            old_mph = recent_speeds.pop(0)
                            accel_mph_s = (mph - old_mph) / (window_size / fps)
                        else:
                            accel_mph_s = 0.0
                            
                        # Speed Bursts
                        if accel_mph_s > 6.0 and not hist.get("in_burst", False):
                            player_stats[pid]["speed_bursts"] += 1
                            hist["in_burst"] = True
                        elif accel_mph_s < 1.0:
                            hist["in_burst"] = False
                            
                hist["last_real_x"] = p["real_x"]
                hist["last_real_y"] = p["real_y"]
                hist["last_frame"] = f_idx

            # Possession Heuristics
            p["has_puck"] = False
            if homography_matrix is not None and len(real_pucks) > 0:
                for puck in real_pucks:
                    dist_to_puck = calculate_distance((p["real_x"], p["real_y"]), (puck["real_x"], puck["real_y"]))
                    if dist_to_puck < 6.0:
                        p["has_puck"] = True
                        player_stats[pid]["possession_frames"] += 1
                        frame_possessor = pid
                        break
                        
            # Contact Heuristics
            p["in_contact"] = False
            if homography_matrix is not None:
                for other_p in frame_obj.get("players", []):
                    if other_p["id"] != pid:
                        ox = other_p.get("real_x")
                        oy = other_p.get("real_y")
                        if ox is not None and oy is not None:
                            dist_to_other = calculate_distance((p["real_x"], p["real_y"]), (ox, oy))
                            if dist_to_other < 3.0:
                                p["in_contact"] = True
                                break
                        
        if homography_matrix is not None and frame_possessor != current_possessor and frame_possessor is not None:
            timeline_events.append({
                "type": "possession_gained",
                "frame": f_idx,
                "player_id": frame_possessor
            })
            current_possessor = frame_possessor
                        
    # Finalize shifts and round off stats
    for pid, stats in player_stats.items():
        if pid in player_history:
            hist = player_history[pid]
            shift_duration = hist["last_frame"] - stats["current_shift_start"]
            if shift_duration > fps * 5.0:
                stats["shifts"].append({
                    "start_frame": stats["current_shift_start"],
                    "end_frame": hist["last_frame"],
                    "duration_sec": round(shift_duration / fps, 1)
                })

        stats["total_distance_ft"] = round(stats["total_distance_ft"], 2)
        stats["possession_time_sec"] = round(stats["possession_frames"] / fps, 2)
        stats["energizer_ratio"] = round(stats["active_frames"] / max(1, stats["total_frames_on_ice"]), 2)
        
        stats["radar_scores"] = {
            "hustle": min(100, int((stats["total_distance_ft"] / 3000.0) * 100)),
            "speed": min(100, int((stats["speed_bursts"] / 10.0) * 100)),
            "energizer": int(stats["energizer_ratio"] * 100)
        }
        
        del stats["possession_frames"]
        del stats["current_shift_start"]
        del stats["active_frames"]
                        
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
