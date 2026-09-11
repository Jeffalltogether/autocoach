import cv2
import numpy as np
import json
import argparse
import os

# Global variables to store user clicks
clicked_points = []
clone_img = None

def mouse_callback(event, x, y, flags, param):
    global clicked_points, clone_img
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(clicked_points) < 4:
            clicked_points.append((x, y))
            cv2.circle(clone_img, (x, y), 5, (0, 255, 0), -1)
            cv2.putText(clone_img, str(len(clicked_points)), (x+10, y-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.imshow("Calibration - Click 4 points", clone_img)

def main():
    parser = argparse.ArgumentParser(description="Interactive Rink Calibration")
    parser.add_argument("--video", type=str, required=True, help="Path to raw video file")
    parser.add_argument("--out", type=str, default="../data/processed/homography.json", help="Output JSON for homography matrix")
    parser.add_argument("--width", type=float, default=100.0, help="Real-world width of the selected area (e.g., feet)")
    parser.add_argument("--height", type=float, default=100.0, help="Real-world height of the selected area (e.g., feet)")
    args = parser.parse_args()

    global clone_img, clicked_points
    
    # 1. Extract first frame
    cap = cv2.VideoCapture(args.video)
    success, frame = cap.read()
    cap.release()
    
    if not success:
        print(f"Error: Could not read video {args.video}")
        return
        
    clone_img = frame.copy()
    
    print("\n" + "="*40)
    print("🏒 INTERACTIVE RINK CALIBRATION 🏒")
    print("="*40)
    print("Click 4 corners of your practice zone (like cones) in this EXACT order:")
    print("  1. Top-Left corner")
    print("  2. Top-Right corner")
    print("  3. Bottom-Right corner")
    print("  4. Bottom-Left corner")
    print("\nControls:")
    print("  'c'     - Clear points and start over")
    print("  'ENTER' - Save and calculate matrix (requires 4 points)")
    print("  'q'     - Quit without saving")
    print("="*40 + "\n")
    
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
    
    matrix, status = cv2.findHomography(src_pts, dst_pts)
    
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
