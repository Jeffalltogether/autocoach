import cv2
import numpy as np
import json
import argparse
import os

def nothing(x):
    pass

def main():
    parser = argparse.ArgumentParser(description="Interactive Fisheye Undistortion Tuner")
    parser.add_argument("--video", type=str, required=True, help="Path to raw video file")
    parser.add_argument("--out", type=str, default=None, help="Output json path")
    args = parser.parse_args()

    if args.out is None:
        base_name = os.path.splitext(os.path.basename(args.video))[0]
        args.out = f"../data/processed/{base_name}_camera_calib.json"

    cap = cv2.VideoCapture(args.video)
    success, frame = cap.read()
    cap.release()

    if not success:
        print(f"Error: Could not read video at {args.video}.")
        return

    h, w = frame.shape[:2]
    
    window_name = "Undistort Tuner (Press ENTER to save)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    # We will use sliders from 0 to 2000, where 1000 is the center (0.0 distortion)
    # This gives us a slider range of -1.0 to +1.0 for the coefficients
    cv2.createTrackbar("k1 (Barrel)", window_name, 1000, 2000, nothing)
    cv2.createTrackbar("k2 (Edge Curvature)", window_name, 1000, 2000, nothing)
    
    # Zoom slider to prevent black edges when flattening
    cv2.createTrackbar("Zoom / Scale", window_name, 100, 300, nothing)

    print("\n" + "="*50)
    print("🎥 INTERACTIVE FISHEYE TUNER 🎥")
    print("="*50)
    print("1. Drag 'k1' left or right to flatten the 'barrel' distortion.")
    print("   Look specifically at the blue lines and boards — stop when they are perfectly straight.")
    print("2. Fine-tune with 'k2' if the extreme edges still look warped.")
    print("3. Adjust 'Zoom' if the un-warping pulled the corners too far off screen.")
    print("4. Press 'ENTER' when you are happy to save the profile.")
    print("5. Press 'q' to quit.")
    print("="*50 + "\n")

    while True:
        # Calculate raw values from sliders
        k1_val = (cv2.getTrackbarPos("k1 (Barrel)", window_name) - 1000) / 1000.0
        k2_val = (cv2.getTrackbarPos("k2 (Edge Curvature)", window_name) - 1000) / 1000.0
        zoom_val = cv2.getTrackbarPos("Zoom / Scale", window_name) / 100.0
        
        if zoom_val <= 0.1: zoom_val = 0.1

        # Intrinsic Camera Matrix (K)
        # Using a guessed focal length based on video width and zoom
        fx = w * zoom_val
        fy = h * zoom_val
        cx = w / 2.0
        cy = h / 2.0
        
        K = np.array([
            [fx, 0, cx],
            [0, fy, cy],
            [0,  0,  1]
        ], dtype=np.float32)

        # Distortion Coefficients (D) - [k1, k2, p1, p2, k3]
        D = np.array([k1_val, k2_val, 0, 0, 0], dtype=np.float32)

        # Apply OpenCV's undistortion math
        undistorted = cv2.undistort(frame, K, D)

        # Show the result in real-time
        cv2.imshow(window_name, undistorted)
        
        key = cv2.waitKey(30) & 0xFF
        if key == ord('q'):
            print("Tuning aborted.")
            break
        elif key == 13: # ENTER key
            os.makedirs(os.path.dirname(args.out), exist_ok=True)
            calib_data = {
                "video": args.video,
                "K": K.tolist(),
                "D": D.tolist(),
                "k1": k1_val,
                "k2": k2_val,
                "zoom": zoom_val
            }
            with open(args.out, "w") as f:
                json.dump(calib_data, f, indent=4)
            print(f"\n✅ Success! Camera calibration profile saved to {args.out}")
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
