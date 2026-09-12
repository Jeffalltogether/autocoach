import argparse
import json
import os

import cv2
import numpy as np

# Global variables to store user clicks
clicked_points = []
clone_img = None

def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and len(clicked_points) < 4:
        clicked_points.append((x, y))
        cv2.circle(clone_img, (x, y), 5, (0, 255, 0), -1)
        cv2.putText(clone_img, str(len(clicked_points)), (x+10, y-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow("Calibration - Click 4 points", clone_img)

def main():
    parser = argparse.ArgumentParser(description="Interactive Rink Calibration")
    parser.add_argument("--video", type=str, required=True, help="Path to video file")
    parser.add_argument("--out", type=str, default=None, help="Output JSON for homography matrix")
    parser.add_argument("--width", type=float, default=50.0, help="Real-world length of the selected area (e.g., feet, usually 50 for blue-to-blue)")
    parser.add_argument("--height", type=float, default=85.0, help="Real-world width of the selected area (e.g., feet, usually 85 for boards-to-boards)")
    parser.add_argument("--camera_calib", type=str, default=None, help="Path to camera_calibration.json if flattening fisheye first")
    args = parser.parse_args()
    
    if args.out is None:
        base_name = os.path.splitext(os.path.basename(args.video))[0]
        args.out = f"../data/processed/{base_name}_homography.json"

    global clone_img, clicked_points
    
    # 1. Extract first frame
    cap = cv2.VideoCapture(args.video)
    success, frame = cap.read()
    cap.release()
    
    if not success:
        print(f"Error: Could not read video {args.video}")
        return

    # 1.5 Undistort frame if calibration is provided
    if args.camera_calib and os.path.exists(args.camera_calib):
        with open(args.camera_calib, "r") as f:
            calib = json.load(f)
        K = np.array(calib["K"], dtype=np.float32)
        D = np.array(calib["D"], dtype=np.float32)
        frame = cv2.undistort(frame, K, D)
        print(f"Applied fisheye correction from {args.camera_calib}")
        
    clone_img = frame.copy()
    
    print("\n" + "="*60)
    print("🏒 INTERACTIVE RINK CALIBRATION 🏒")
    print("="*60)
    print("RECOMMENDED: The Neutral Zone Method")
    print("For a standard NHL/USA Hockey rink, the neutral zone is 85 ft wide")
    print("by 50 ft long. Pass these exact dimensions to the script:")
    print("   --width 85 --height 50\n")
    print("Click the 4 corners where the BLUE LINES intersect the BOARDS:")
    print("  1. Top-Left (Left blue line & top boards)")
    print("  2. Top-Right (Right blue line & top boards)")
    print("  3. Bottom-Right (Right blue line & bottom boards)")
    print("  4. Bottom-Left (Left blue line & bottom boards)")
    print("\nControls:")
    print("  'c'     - Clear points and start over")
    print("  'ENTER' - Save and calculate matrix (requires 4 points)")
    print("  'q'     - Quit without saving")
    print("="*60 + "\n")
    
    window_name = "Calibration - Click 4 points"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window_name, mouse_callback)
    
    while True:
        cv2.imshow(window_name, clone_img)
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord("c"):
            clicked_points = []
            clone_img = frame.copy()
            print("Points cleared. Start again.")
        elif key == ord("q"):
            print("Calibration aborted.")
            cv2.destroyAllWindows()
            return
        elif key == 13: # 13 is the ENTER key
            if len(clicked_points) == 4:
                break
            else:
                print(f"You need exactly 4 points. You only have {len(clicked_points)}.")
                
    cv2.destroyAllWindows()
        
    # 2. Compute Homography Matrix
    src_pts = np.array(clicked_points, dtype=np.float32)
    
    # Create destination points based on real-world dimensions
    # Assuming origin (0,0) is top-left
    dst_pts = np.array([
        [0, 0],
        [args.width, 0],
        [args.width, args.height],
        [0, args.height]
    ], dtype=np.float32)
    
    matrix, _status = cv2.findHomography(src_pts, dst_pts)
    
    if matrix is None:
        print("Error: Could not compute homography matrix from those points.")
        return
        
    # 3. Save to JSON
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    homography_data = {
        "video": args.video,
        "real_world_width": args.width,
        "real_world_height": args.height,
        "src_points": clicked_points,
        "homography_matrix": matrix.tolist()
    }
    
    with open(args.out, "w") as f:
        json.dump(homography_data, f, indent=4)
        
    print(f"\n✅ Success! Homography matrix saved to {args.out}")
    print("This matrix will now be used by the pipeline to convert screen pixels into physical tracking metrics!")

if __name__ == "__main__":
    main()
