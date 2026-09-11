import numpy as np
import cv2

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
                    stick_blade = None
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
                        
        # --- 3. Timeline Event Generation (Possession Changes) ---
        if homography_matrix is not None:
            if frame_possessor != current_possessor and frame_possessor is not None:
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
            "fps": fps
        },
        "player_stats": player_stats,
        "timeline_events": timeline_events,
        "frames": frames_data
    }
    
    return final_output
