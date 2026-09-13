import cv2
import argparse
import numpy as np
import json
import os

def select_roi(video_path, out_path):
    cap = cv2.VideoCapture(video_path)
    success, frame = cap.read()
    if not success:
        print(f"Error reading video: {video_path}")
        return

    # Resize frame if it's too large for standard screens (e.g., 4K)
    display_scale = 1.0
    max_height = 900
    if frame.shape[0] > max_height:
        display_scale = max_height / frame.shape[0]
        display_frame = cv2.resize(frame, (0, 0), fx=display_scale, fy=display_scale)
    else:
        display_frame = frame.copy()

    polygon_points = []
    
    def mouse_callback(event, x, y, flags, param):
        nonlocal display_frame
        
        if event == cv2.EVENT_LBUTTONDOWN:
            # Map back to original resolution
            orig_x = int(x / display_scale)
            orig_y = int(y / display_scale)
            polygon_points.append([orig_x, orig_y])
            
            # Redraw
            temp_frame = display_frame.copy()
            pts = np.array([[int(px * display_scale), int(py * display_scale)] for px, py in polygon_points], np.int32)
            
            if len(pts) > 0:
                for pt in pts:
                    cv2.circle(temp_frame, tuple(pt), 4, (0, 0, 255), -1)
            
            if len(pts) > 1:
                cv2.polylines(temp_frame, [pts], isClosed=False, color=(0, 255, 0), thickness=2)
                
            cv2.imshow("ROI Selector", temp_frame)

    cv2.namedWindow("ROI Selector")
    cv2.setMouseCallback("ROI Selector", mouse_callback)
    
    print("\n--- HockeyAI: ROI Masking ---")
    print("Click along the perimeter of the ice sheet to draw a polygon.")
    print("Press 'c' to close the polygon and save.")
    print("Press 'r' to reset points.")
    print("Press 'q' to quit without saving.\n")

    cv2.imshow("ROI Selector", display_frame)

    while True:
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('c'):
            if len(polygon_points) > 2:
                # Draw final closed polygon
                temp_frame = display_frame.copy()
                pts = np.array([[int(px * display_scale), int(py * display_scale)] for px, py in polygon_points], np.int32)
                cv2.polylines(temp_frame, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
                cv2.imshow("ROI Selector", temp_frame)
                cv2.waitKey(500)
                
                # Save to JSON
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "w") as f:
                    json.dump({"roi_polygon": polygon_points}, f, indent=4)
                print(f"✅ Saved ROI polygon to {out_path}")
            else:
                print("⚠️ Please click at least 3 points to form a polygon.")
            break
            
        elif key == ord('r'):
            polygon_points = []
            cv2.imshow("ROI Selector", display_frame)
            print("Points reset.")
            
        elif key == ord('q'):
            print("Cancelled.")
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    select_roi(args.video, args.out)
