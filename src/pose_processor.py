"""
MediaPipe pose processing module
Extracts body landmarks from video frames
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import List, Dict, Tuple


class PoseProcessor:
    """Processes video frames to extract pose landmarks using MediaPipe"""
    
    def __init__(self, model_complexity=2, 
                 min_detection_confidence=0.5,
                 min_tracking_confidence=0.5):
        """
        Initialize MediaPipe Pose
        
        Args:
            model_complexity: 0=lite, 1=full, 2=heavy (more accurate)
            min_detection_confidence: Minimum confidence for detection
            min_tracking_confidence: Minimum confidence for tracking
        """
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        self.pose = self.mp_pose.Pose(
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            smooth_landmarks=True
        )
        
        # Store processed results
        self.landmarks_sequence = []
        
    def process_frame(self, frame):
        """
        Process a single frame
        
        Args:
            frame: BGR image from OpenCV
            
        Returns:
            results: MediaPipe pose results
            annotated_frame: Frame with landmarks drawn
        """
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        results = self.pose.process(image_rgb)
        
        # Draw landmarks on frame
        annotated_frame = frame.copy()
        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                annotated_frame,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
            )
        
        return results, annotated_frame
    
    def process_video(self, video_path):
        """
        Process entire video file
        
        Args:
            video_path: Path to video file
            
        Returns:
            landmarks_sequence: List of landmark dictionaries for each frame
            annotated_frames: List of frames with landmarks drawn
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video: {video_path}")
        
        landmarks_sequence = []
        annotated_frames = []
        frame_count = 0
        
        print(f"Processing video: {video_path}")
        
        while cap.isOpened():
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Process frame
            results, annotated_frame = self.process_frame(frame)
            
            # Extract landmarks
            if results.pose_landmarks:
                landmarks_dict = self._extract_landmarks(results.pose_landmarks)
                landmarks_sequence.append(landmarks_dict)
                annotated_frames.append(annotated_frame)
            else:
                landmarks_sequence.append(None)
                annotated_frames.append(frame)
            
            frame_count += 1
            
            if frame_count % 30 == 0:
                print(f"  Processed {frame_count} frames...")
        
        cap.release()
        print(f"Video processing complete: {frame_count} frames")
        
        return landmarks_sequence, annotated_frames
    
    def _extract_landmarks(self, pose_landmarks):
        """
        Extract landmark coordinates into a dictionary
        
        Args:
            pose_landmarks: MediaPipe pose landmarks
            
        Returns:
            Dictionary with landmark names and coordinates
        """
        landmarks = {}
        
        # Key landmarks we care about for golf swing
        landmark_names = {
            11: 'left_shoulder',
            12: 'right_shoulder',
            23: 'left_hip',
            24: 'right_hip',
            15: 'left_wrist',
            16: 'right_wrist',
            0: 'nose',
            7: 'left_ear',
            8: 'right_ear'
        }
        
        for idx, name in landmark_names.items():
            landmark = pose_landmarks.landmark[idx]
            landmarks[name] = {
                'x': landmark.x,
                'y': landmark.y,
                'z': landmark.z,
                'visibility': landmark.visibility
            }
        
        return landmarks
    
    def get_landmark_point(self, landmarks_dict, landmark_name, frame_shape):
        """
        Convert normalized landmark to pixel coordinates
        
        Args:
            landmarks_dict: Dictionary of landmarks
            landmark_name: Name of landmark (e.g., 'left_hip')
            frame_shape: Shape of frame (height, width, channels)
            
        Returns:
            (x, y) pixel coordinates
        """
        if landmarks_dict is None or landmark_name not in landmarks_dict:
            return None
        
        height, width = frame_shape[:2]
        landmark = landmarks_dict[landmark_name]
        
        x = int(landmark['x'] * width)
        y = int(landmark['y'] * height)
        
        return (x, y)
    
    def release(self):
        """Release MediaPipe resources"""
        self.pose.close()

