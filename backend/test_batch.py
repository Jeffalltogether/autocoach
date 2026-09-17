import cv2
import numpy as np
from ultralytics import YOLO

detector = YOLO("yolov8n.pt")
pose_model = YOLO("yolov8n-pose.pt")

frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
# Add some fake boxes
boxes = [[100, 100, 200, 300], [400, 100, 500, 300]]
crops = []
offsets = []
for box in boxes:
    x1, y1, x2, y2 = box
    crops.append(frame[y1:y2, x1:x2])
    offsets.append((x1, y1))

if crops:
    results = pose_model(crops, verbose=False)
    for i, res in enumerate(results):
        if res.keypoints is not None:
            print(f"Crop {i} keypoints shape: {res.keypoints.data.shape}")

