import cv2
import numpy as np
import json
import argparse
import os

def main():
    parser = argparse.ArgumentParser(description="Generate a Top-Down Birds-Eye Video")
    parser.add_argument("--video", type=str, required=True, help="Path to raw video file")
    parser.add_argument("--homography", type=str, required=True, help="Path to homography.json")
    parser.add_argument("--camera_calib", type=str, default=None, help="Path to camera_calibration.json")
    parser.add_argument("--out", type=str, default="../data/processed/birds_eye_output.mp4")
    parser.add_argument("--scale", type=int, default=15, help="Pixels per real-world foot")
    args = parser.parse_args()

    # Load Homography
    with open(args.homography, "r") as f:
        homog_data = json.load(f)
        H_feet = np.array(homog_data["homography_matrix"], dtype=np.float32)
        real_w = homog_data.get("real_world_width", 85.0)
        real_h = homog_data.get("real_world_height", 50.0)

    # Load Camera Calibration
    cam_K, cam_D = None, None
    if args.camera_calib and os.path.exists(args.camera_calib):
        with open(args.camera_calib, "r") as f:
            calib = json.load(f)
            cam_K = np.array(calib["K"], dtype=np.float32)
            cam_D = np.array(calib["D"], dtype=np.float32)

    # We need to scale the Homography from feet to pixels for the output video
    # e.g., 85 feet wide * 15 pixels/foot = 1275 pixels wide
    out_width = int(real_w * args.scale)
    out_height = int(real_h * args.scale)
    
    scale_matrix = np.array([
        [args.scale, 0, 0],
        [0, args.scale, 0],
        [0, 0, 1]
    ], dtype=np.float32)
    
    H_pixels = scale_matrix @ H_feet

    cap = cv2.VideoCapture(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(args.out, fourcc, fps, (out_width, out_height))

    print(f"Rendering {out_width}x{out_height} birds-eye video...")
    
    frame_idx = 0
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
            
        # 1. Flatten fisheye (if provided)
        if cam_K is not None:
            frame = cv2.undistort(frame, cam_K, cam_D)
            
        # 2. Warp into perfect 2D top-down rectangle
        warped = cv2.warpPerspective(frame, H_pixels, (out_width, out_height))
        
        out.write(warped)
        frame_idx += 1
        
        if frame_idx % 30 == 0:
            print(f"Rendered {frame_idx} frames...")
            
    cap.release()
    out.release()
    print(f"✅ Top-down video saved to {args.out}")

if __name__ == "__main__":
    main()
