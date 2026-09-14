import argparse
import json
import os
import cv2
import numpy as np

def select_roi(frame, display_scale, display_frame, out_path):
    polygon_points = []
    
    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            orig_x = int(x / display_scale)
            orig_y = int(y / display_scale)
            polygon_points.append([orig_x, orig_y])
            
            temp_frame = display_frame.copy()
            pts = np.array([[int(px * display_scale), int(py * display_scale)] for px, py in polygon_points], np.int32)
            
            for pt in pts:
                cv2.circle(temp_frame, tuple(pt), 4, (0, 0, 255), -1)
            
            if len(pts) > 1:
                cv2.polylines(temp_frame, [pts], isClosed=False, color=(0, 255, 0), thickness=2)
                
            cv2.imshow("STEP 1: ROI Selector", temp_frame)

    cv2.namedWindow("STEP 1: ROI Selector")
    cv2.setMouseCallback("STEP 1: ROI Selector", mouse_callback)
    
    print("\n" + "="*60)
    print("STEP 1: REGION OF INTEREST (ROI) MASKING")
    print("="*60)
    print("Click along the perimeter of the ice sheet to draw a polygon.")
    print("This ignores players in the stands or on the bench.")
    print("\nControls:")
    print("  'ENTER' - Close the polygon and save")
    print("  'r'     - Reset points")
    print("  'q'     - Quit completely")
    print("="*60 + "\n")

    cv2.imshow("STEP 1: ROI Selector", display_frame)

    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == 13: # ENTER
            if len(polygon_points) > 2:
                temp_frame = display_frame.copy()
                pts = np.array([[int(px * display_scale), int(py * display_scale)] for px, py in polygon_points], np.int32)
                cv2.polylines(temp_frame, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
                cv2.imshow("STEP 1: ROI Selector", temp_frame)
                cv2.waitKey(500)
                
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "w") as f:
                    json.dump({"roi_polygon": polygon_points}, f, indent=4)
                print(f"✅ Saved ROI polygon to {out_path}")
                cv2.destroyAllWindows()
                return True
            else:
                print("⚠️ Please click at least 3 points to form a polygon.")
        elif key == ord('r'):
            polygon_points = []
            cv2.imshow("STEP 1: ROI Selector", display_frame)
            print("Points reset.")
        elif key == ord('q'):
            print("Cancelled.")
            cv2.destroyAllWindows()
            return False

def select_homography(frame, display_scale, display_frame, out_path, real_width, real_height):
    clicked_points = []
    
    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(clicked_points) < 4:
            orig_x = int(x / display_scale)
            orig_y = int(y / display_scale)
            clicked_points.append([orig_x, orig_y])
            
            temp_frame = display_frame.copy()
            pts = np.array([[int(px * display_scale), int(py * display_scale)] for px, py in clicked_points], np.int32)
            
            for i, pt in enumerate(pts):
                cv2.circle(temp_frame, tuple(pt), 5, (0, 255, 0), -1)
                cv2.putText(temp_frame, str(i+1), (pt[0]+10, pt[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
            cv2.imshow("STEP 2: Homography Calibration", temp_frame)

    cv2.namedWindow("STEP 2: Homography Calibration")
    cv2.setMouseCallback("STEP 2: Homography Calibration", mouse_callback)
    
    print("\n" + "="*60)
    print("STEP 2: HOMOGRAPHY CALIBRATION")
    print("="*60)
    print("Click exactly 4 corners of a known rectangle on the ice.")
    print("Default dimensions assume the Neutral Zone (50ft length x 85ft width).")
    print("Click order: Top-Left -> Top-Right -> Bottom-Right -> Bottom-Left")
    print("\nControls:")
    print("  'ENTER' - Save and calculate matrix (requires 4 points)")
    print("  'r'     - Clear points and start over")
    print("  'q'     - Quit")
    print("="*60 + "\n")

    cv2.imshow("STEP 2: Homography Calibration", display_frame)

    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == 13: # ENTER
            if len(clicked_points) == 4:
                src_pts = np.array(clicked_points, dtype=np.float32)
                dst_pts = np.array([
                    [0, 0],
                    [real_width, 0],
                    [real_width, real_height],
                    [0, real_height]
                ], dtype=np.float32)
                
                matrix, _status = cv2.findHomography(src_pts, dst_pts)
                
                if matrix is None:
                    print("Error: Could not compute homography matrix from those points.")
                    return False
                    
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                homography_data = {
                    "real_world_width": real_width,
                    "real_world_height": real_height,
                    "src_points": clicked_points,
                    "homography_matrix": matrix.tolist()
                }
                
                with open(out_path, "w") as f:
                    json.dump(homography_data, f, indent=4)
                    
                print(f"✅ Success! Homography matrix saved to {out_path}")
                cv2.destroyAllWindows()
                return True
            else:
                print(f"⚠️ You need exactly 4 points. You only have {len(clicked_points)}.")
        elif key == ord('r'):
            clicked_points = []
            cv2.imshow("STEP 2: Homography Calibration", display_frame)
            print("Points reset.")
        elif key == ord('q'):
            print("Cancelled.")
            cv2.destroyAllWindows()
            return False

def main():
    parser = argparse.ArgumentParser(description="Interactive Rink Calibration Suite")
    parser.add_argument("--video", type=str, required=True, help="Path to video file")
    parser.add_argument("--width", type=float, default=50.0, help="Real-world length of the selected area (e.g., feet, usually 50 for neutral zone)")
    parser.add_argument("--height", type=float, default=85.0, help="Real-world width of the selected area (e.g., feet, usually 85 for neutral zone)")
    parser.add_argument("--camera_calib", type=str, default=None, help="Path to camera_calibration.json if flattening fisheye first")
    args = parser.parse_args()
    
    # Auto-generate paths in data/calibration/
    base_name = os.path.splitext(os.path.basename(args.video))[0]
    calib_dir = os.path.abspath(os.path.join(os.path.dirname(args.video), "..", "calibration"))
    os.makedirs(calib_dir, exist_ok=True)
    
    roi_out = os.path.join(calib_dir, f"{base_name}_roi.json")
    homography_out = os.path.join(calib_dir, f"{base_name}_homography.json")

    cap = cv2.VideoCapture(args.video)
    success, frame = cap.read()
    cap.release()
    
    if not success:
        print(f"Error: Could not read video {args.video}")
        return

    # Undistort frame if calibration is provided
    if args.camera_calib and os.path.exists(args.camera_calib):
        with open(args.camera_calib, "r") as f:
            calib = json.load(f)
        K = np.array(calib["K"], dtype=np.float32)
        D = np.array(calib["D"], dtype=np.float32)
        frame = cv2.undistort(frame, K, D)
        print(f"Applied fisheye correction from {args.camera_calib}")
        
    # Resize frame for standard screens
    display_scale = 1.0
    max_height = 900
    if frame.shape[0] > max_height:
        display_scale = max_height / frame.shape[0]
        display_frame = cv2.resize(frame, (0, 0), fx=display_scale, fy=display_scale)
    else:
        display_frame = frame.copy()

    # Step 1
    success = select_roi(frame, display_scale, display_frame, roi_out)
    if not success:
        return
        
    # Step 2
    select_homography(frame, display_scale, display_frame, homography_out, args.width, args.height)

if __name__ == "__main__":
    main()
