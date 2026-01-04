"""
Example: Process dual camera recordings with MediaPipe
This script demonstrates how to analyze the synchronized videos with MediaPipe
"""

import cv2
import mediapipe as mp
import os
import sys


def process_dual_videos(video1_path: str, video2_path: str, output_dir: str = "mediapipe_output"):
    """
    Process two synchronized videos with MediaPipe Pose estimation
    
    Args:
        video1_path: Path to first camera video
        video2_path: Path to second camera video
        output_dir: Directory to save processed videos
    """
    # Initialize MediaPipe
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    pose = mp_pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    # Open video files
    cap1 = cv2.VideoCapture(video1_path)
    cap2 = cv2.VideoCapture(video2_path)
    
    if not cap1.isOpened() or not cap2.isOpened():
        print("Error: Could not open video files")
        return
    
    # Get video properties
    fps = int(cap1.get(cv2.CAP_PROP_FPS))
    width = int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap1.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Setup output video writers
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    output1_path = os.path.join(output_dir, "processed_camera1.mp4")
    output2_path = os.path.join(output_dir, "processed_camera2.mp4")
    
    out1 = cv2.VideoWriter(output1_path, fourcc, fps, (width, height))
    out2 = cv2.VideoWriter(output2_path, fourcc, fps, (width, height))
    
    frame_count = 0
    
    print("Processing videos with MediaPipe...")
    print("Press 'q' to quit early")
    
    while True:
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()
        
        if not (ret1 and ret2):
            break
        
        # Convert BGR to RGB for MediaPipe
        rgb_frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)
        rgb_frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        results1 = pose.process(rgb_frame1)
        results2 = pose.process(rgb_frame2)
        
        # Draw pose landmarks
        if results1.pose_landmarks:
            mp_drawing.draw_landmarks(
                frame1, results1.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2)
            )
        
        if results2.pose_landmarks:
            mp_drawing.draw_landmarks(
                frame2, results2.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2)
            )
        
        # Write processed frames
        out1.write(frame1)
        out2.write(frame2)
        
        # Display preview (optional)
        if frame_count % 30 == 0:  # Show every 30th frame
            display1 = cv2.resize(frame1, (640, 360))
            display2 = cv2.resize(frame2, (640, 360))
            combined = cv2.hstack([display1, display2])
            cv2.imshow('MediaPipe Processing', combined)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        frame_count += 1
        
        if frame_count % 100 == 0:
            print(f"Processed {frame_count} frames...")
    
    # Cleanup
    cap1.release()
    cap2.release()
    out1.release()
    out2.release()
    cv2.destroyAllWindows()
    pose.close()
    
    print(f"\nProcessing complete!")
    print(f"Processed {frame_count} frames")
    print(f"Output saved to:")
    print(f"  {output1_path}")
    print(f"  {output2_path}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python mediapipe_example.py <video1_path> <video2_path>")
        print("\nExample:")
        print("  python mediapipe_example.py recordings/dual_capture_20240101_120000_camera1.mp4 recordings/dual_capture_20240101_120000_camera2.mp4")
        return
    
    video1_path = sys.argv[1]
    video2_path = sys.argv[2]
    
    if not os.path.exists(video1_path) or not os.path.exists(video2_path):
        print("Error: One or both video files not found")
        return
    
    process_dual_videos(video1_path, video2_path)


if __name__ == "__main__":
    main()

