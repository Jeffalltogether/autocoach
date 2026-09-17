import cv2
import numpy as np
from ultralytics import YOLO
import urllib.request

# Download a real image
urllib.request.urlretrieve("https://ultralytics.com/images/bus.jpg", "bus.jpg")
frame = cv2.imread("bus.jpg")

detector = YOLO("yolov8n.pt")
pose_model = YOLO("yolov8n-pose.pt")

# Step 1: Detect and Track
track_results = detector.track(frame, persist=True, classes=[0], verbose=False)
boxes = track_results[0].boxes.xyxy.cpu().numpy()

# Step 2: Batched Pose on Crops
crops = []
offsets = []
for box in boxes:
    x1, y1, x2, y2 = [int(v) for v in box]
    crop = frame[max(0, y1-10):min(frame.shape[0], y2+10), max(0, x1-10):min(frame.shape[1], x2+10)]
    crops.append(crop)
    offsets.append((x1-10, y1-10))

if crops:
    pose_results = pose_model(crops, verbose=False)
    for i, res in enumerate(pose_results):
        if res.keypoints is not None and len(res.keypoints) > 0:
            kpts = res.keypoints.data[0].cpu().numpy()
            print(f"Crop {i} detected {len(kpts)} keypoints")
        else:
            print(f"Crop {i} no keypoints")
