import cv2
from ultralytics import YOLO

model = YOLO("yolov8n-pose.pt")
frame = cv2.imread("test.jpg") # We don't have a video, just an empty frame
import numpy as np
frame = np.zeros((480, 640, 3), dtype=np.uint8)
results = model.track(frame, persist=True)

print("Boxes:", results[0].boxes)
print("Keypoints:", results[0].keypoints)
