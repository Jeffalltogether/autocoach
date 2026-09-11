import cv2
import json
from ultralytics import YOLO
from pathlib import Path

def main():
    print("Starting main...", flush=True)
    video_path = "../data/raw/hocky_test_video.mp4"
    output_video_path = "../data/processed/hockey_test_pose_output.mp4"
    output_json_path = "../data/processed/hockey_test_pose_tracking.json"
    
    print(f"Loading YOLOv8n-pose model...", flush=True)
    # yolov8n-pose.pt supports both bounding box tracking and 17-point human pose estimation
    model = YOLO("yolov8n-pose.pt") 
    print("Model loaded.", flush=True)
    
    print(f"Opening video: {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video file: {video_path}")
        return
        
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
    
    tracking_data = []
    frame_idx = 0
    
    print(f"Starting pose tracking processing...")
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        # Run pose tracking on frame using CPU to prevent Metal (MPS) deadlocks
        results = model.track(frame, persist=True, classes=[0], verbose=False, device='cpu')
        
        # Annotate the frame with bounding boxes, IDs, and skeletal poses
        annotated_frame = results[0].plot()
        
        frame_data = {
            "frame": frame_idx,
            "players": []
        }
        
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xywh.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            
            # Extract keypoints if available
            has_keypoints = results[0].keypoints is not None
            if has_keypoints:
                keypoints_batch = results[0].keypoints.data.cpu().numpy()
            
            for i, (box, track_id) in enumerate(zip(boxes, track_ids)):
                x, y, w, h = [float(v) for v in box]
                
                player_dict = {
                    "id": track_id,
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                }
                
                # Add pose data (17 keypoints per person: nose, shoulders, elbows, wrists, etc.)
                if has_keypoints and i < len(keypoints_batch):
                    kpts_list = []
                    for kpt in keypoints_batch[i]:
                        kx, ky, conf = [float(v) for v in kpt]
                        kpts_list.append({"x": kx, "y": ky, "conf": conf})
                    player_dict["keypoints"] = kpts_list

                frame_data["players"].append(player_dict)
        
        tracking_data.append(frame_data)
        out.write(annotated_frame)
        
        frame_idx += 1
        if frame_idx % 100 == 0:
            print(f"Processed {frame_idx} frames...", flush=True)

    cap.release()
    out.release()
    
    with open(output_json_path, "w") as f:
        json.dump(tracking_data, f, indent=2)
        
    print(f"Processing complete.")
    print(f"Video saved to {output_video_path}")
    print(f"Data saved to {output_json_path}")

if __name__ == "__main__":
    main()
