import sys
with open('debug.log', 'w') as f:
    f.write('Starting...\n')
    f.flush()
    try:
        import cv2
        f.write('cv2 imported\n')
        f.flush()
    except Exception as e:
        f.write(f'cv2 error: {e}\n')
    try:
        import torch
        f.write('torch imported\n')
        f.flush()
    except Exception as e:
        f.write(f'torch error: {e}\n')
    try:
        from ultralytics import YOLO
        f.write('YOLO imported\n')
        f.flush()
    except Exception as e:
        f.write(f'YOLO error: {e}\n')
