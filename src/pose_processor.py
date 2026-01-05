"""
MediaPipe pose processing module
Extracts body landmarks from video frames

Note: MediaPipe 0.10.30+ requires downloading model files separately.
Models can be downloaded from: https://github.com/google/mediapipe/tree/master/mediapipe/modules/pose_landmarker
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
from typing import List, Dict, Tuple, Optional
import os
import urllib.request


def get_model_path(model_complexity=2, models_dir=None):
    """
    Get path to MediaPipe pose model file, downloading if necessary
    
    Args:
        model_complexity: 0=lite, 1=full, 2=heavy
        models_dir: Directory to store models (default: models/ in project root)
        
    Returns:
        Path to model file (.task)
    """
    # Model URLs from MediaPipe repository
    MODEL_URLS = {
        0: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
        1: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task",
        2: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task",
    }
    
    MODEL_NAMES = {
        0: "pose_landmarker_lite.task",
        1: "pose_landmarker_full.task",
        2: "pose_landmarker_heavy.task",
    }
    
    if models_dir is None:
        # Default to models/ directory in project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        models_dir = os.path.join(project_root, "models")
    
    os.makedirs(models_dir, exist_ok=True)
    
    model_name = MODEL_NAMES.get(model_complexity, MODEL_NAMES[2])
    model_path = os.path.join(models_dir, model_name)
    
    # Download model if it doesn't exist
    if not os.path.exists(model_path):
        print(f"Downloading MediaPipe pose model ({model_name})...")
        print(f"This is a one-time download (~30MB)")
        try:
            url = MODEL_URLS.get(model_complexity, MODEL_URLS[2])
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            with urllib.request.urlopen(req, timeout=30) as response:
                with open(model_path, 'wb') as f:
                    f.write(response.read())
            print(f"Model downloaded to: {model_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to download MediaPipe model: {e}")
    
    return model_path


class PoseProcessor:
    """Processes video frames to extract pose landmarks using MediaPipe"""
    
    # Default model paths (users need to download these)
    MODEL_PATHS = {
        0: None,  # Lite model - download from MediaPipe repository
        1: None,  # Full model - download from MediaPipe repository  
        2: None,  # Heavy model - download from MediaPipe repository
    }
    
    def __init__(self, model_complexity=2, 
                 min_detection_confidence=0.5,
                 min_tracking_confidence=0.5,
                 model_path: Optional[str] = None):
        """
        Initialize MediaPipe Pose
        
        Args:
            model_complexity: 0=lite, 1=full, 2=heavy (not used in 0.10.30+ API)
            min_detection_confidence: Minimum confidence for detection (not used in default model)
            min_tracking_confidence: Minimum confidence for tracking (not used in default model)
            model_path: Path to MediaPipe pose model file (.task file)
                       If None, will automatically download the model based on model_complexity
        """
        # MediaPipe 0.10.30+ requires explicit model paths
        if model_path is None:
            # Automatically get/download model
            model_path = get_model_path(model_complexity)
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Use create_from_model_path for simplicity
        # Note: This uses default options (min_detection_confidence and min_tracking_confidence are ignored)
        self.pose_landmarker = vision.PoseLandmarker.create_from_model_path(model_path)
        
        # Store processed results
        self.landmarks_sequence = []
    
    def process_frame(self, frame):
        """
        Process a single frame
        
        Args:
            frame: BGR image from OpenCV
            
        Returns:
            results: MediaPipe pose results (PoseLandmarkerResult)
            annotated_frame: Frame with landmarks drawn
        """
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = image_rgb.shape[:2]
        
        # Convert to MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        
        # Process with MediaPipe
        detection_result = self.pose_landmarker.detect(mp_image)
        
        # Draw landmarks on frame
        annotated_frame = frame.copy()
        pose_landmarks_list = detection_result.pose_landmarks if detection_result.pose_landmarks else []
        
        if pose_landmarks_list:
            for pose_landmarks in pose_landmarks_list:
                # Draw landmarks
                for landmark in pose_landmarks:
                    x = int(landmark.x * w)
                    y = int(landmark.y * h)
                    cv2.circle(annotated_frame, (x, y), 5, (0, 255, 0), -1)
                
                # Draw connections
                connections = vision.PoseLandmarksConnections.POSE_CONNECTIONS
                for connection in connections:
                    start_idx = connection.start
                    end_idx = connection.end
                    if start_idx < len(pose_landmarks) and end_idx < len(pose_landmarks):
                        start_landmark = pose_landmarks[start_idx]
                        end_landmark = pose_landmarks[end_idx]
                        start_point = (int(start_landmark.x * w), int(start_landmark.y * h))
                        end_point = (int(end_landmark.x * w), int(end_landmark.y * h))
                        cv2.line(annotated_frame, start_point, end_point, (0, 255, 0), 2)
        
        # Create a results object similar to the old API for compatibility
        class Results:
            def __init__(self, pose_landmarks):
                self.pose_landmarks = pose_landmarks[0] if pose_landmarks else None
        
        results = Results(pose_landmarks_list)
        
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
            pose_landmarks: MediaPipe pose landmarks list
            
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
            if idx < len(pose_landmarks):
                landmark = pose_landmarks[idx]
                landmarks[name] = {
                    'x': landmark.x,
                    'y': landmark.y,
                    'z': landmark.z,
                    'visibility': landmark.visibility if hasattr(landmark, 'visibility') else 1.0
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
        if hasattr(self, 'pose_landmarker'):
            self.pose_landmarker.close()
