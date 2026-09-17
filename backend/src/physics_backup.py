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
