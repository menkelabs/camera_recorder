"""
Sway calculator module
Calculates lateral sway and rotation metrics from pose landmarks
"""

import numpy as np
from typing import List, Dict, Optional, Tuple


class SwayCalculator:
    """Calculate golf swing biomechanics from pose landmarks"""
    
    def __init__(self):
        self.address_landmarks = None  # Reference position (first frame or manual set)
        
    def set_address_position(self, landmarks: Dict):
        """Set the address position as reference for all measurements"""
        self.address_landmarks = landmarks
        
    def calculate_hip_center(self, landmarks: Dict) -> Optional[Tuple[float, float]]:
        """
        Calculate center point between hips
        
        Args:
            landmarks: Dictionary with left_hip and right_hip
            
        Returns:
            (x, y) normalized coordinates of hip center
        """
        if landmarks is None:
            return None
            
        left_hip = landmarks.get('left_hip')
        right_hip = landmarks.get('right_hip')
        
        if left_hip is None or right_hip is None:
            return None
            
        center_x = (left_hip['x'] + right_hip['x']) / 2
        center_y = (left_hip['y'] + right_hip['y']) / 2
        
        return (center_x, center_y)
    
    def calculate_shoulder_center(self, landmarks: Dict) -> Optional[Tuple[float, float]]:
        """Calculate center point between shoulders"""
        if landmarks is None:
            return None
            
        left_shoulder = landmarks.get('left_shoulder')
        right_shoulder = landmarks.get('right_shoulder')
        
        if left_shoulder is None or right_shoulder is None:
            return None
            
        center_x = (left_shoulder['x'] + right_shoulder['x']) / 2
        center_y = (left_shoulder['y'] + right_shoulder['y']) / 2
        
        return (center_x, center_y)
    
    def calculate_lateral_sway(self, landmarks: Dict, frame_width: int = 1) -> Optional[float]:
        """
        Calculate lateral sway from address position (face-on view)
        
        Positive = sway toward target (left for right-handed)
        Negative = sway away from target (right for right-handed)
        
        Args:
            landmarks: Current frame landmarks
            frame_width: Frame width in pixels for scaling
            
        Returns:
            Lateral sway in pixels (or normalized if frame_width=1)
        """
        if self.address_landmarks is None or landmarks is None:
            return None
            
        current_hip = self.calculate_hip_center(landmarks)
        address_hip = self.calculate_hip_center(self.address_landmarks)
        
        if current_hip is None or address_hip is None:
            return None
            
        # Sway is difference in X position (horizontal movement)
        sway = (current_hip[0] - address_hip[0]) * frame_width
        
        return sway
    
    def calculate_shoulder_turn(self, landmarks: Dict) -> Optional[float]:
        """
        Calculate shoulder rotation angle (degrees)
        
        Based on the apparent width of the shoulder line.
        At address (face-on), shoulders appear widest.
        During backswing, shoulders rotate and appear narrower.
        
        Returns:
            Rotation angle in degrees (0 = address, positive = backswing rotation)
        """
        if landmarks is None:
            return None
            
        left_shoulder = landmarks.get('left_shoulder')
        right_shoulder = landmarks.get('right_shoulder')
        
        if left_shoulder is None or right_shoulder is None:
            return None
            
        # Calculate shoulder width (horizontal distance)
        shoulder_width = abs(right_shoulder['x'] - left_shoulder['x'])
        
        # Use depth (z) to estimate rotation if available
        # MediaPipe z is relative depth - more negative = closer to camera
        z_diff = right_shoulder['z'] - left_shoulder['z']
        
        # Calculate angle from z difference
        # atan2 gives us angle from depth difference
        angle = np.degrees(np.arctan2(z_diff, shoulder_width))
        
        return angle
    
    def calculate_hip_turn(self, landmarks: Dict) -> Optional[float]:
        """
        Calculate hip rotation angle (degrees)
        
        Similar to shoulder turn but for hips.
        Hips rotate less than shoulders in a good golf swing.
        
        Returns:
            Rotation angle in degrees
        """
        if landmarks is None:
            return None
            
        left_hip = landmarks.get('left_hip')
        right_hip = landmarks.get('right_hip')
        
        if left_hip is None or right_hip is None:
            return None
            
        # Calculate hip width
        hip_width = abs(right_hip['x'] - left_hip['x'])
        
        # Use depth difference
        z_diff = right_hip['z'] - left_hip['z']
        
        # Calculate angle
        angle = np.degrees(np.arctan2(z_diff, hip_width))
        
        return angle
    
    def calculate_x_factor(self, landmarks: Dict) -> Optional[float]:
        """
        Calculate X-Factor (shoulder turn - hip turn)
        
        This measures the separation between upper and lower body rotation.
        Higher X-factor = more coil = more potential power.
        
        Returns:
            X-factor in degrees
        """
        shoulder_turn = self.calculate_shoulder_turn(landmarks)
        hip_turn = self.calculate_hip_turn(landmarks)
        
        if shoulder_turn is None or hip_turn is None:
            return None
            
        return abs(shoulder_turn - hip_turn)
    
    def analyze_sequence(self, landmarks_sequence: List[Dict], frame_width: int = 1) -> Dict:
        """
        Analyze a full swing sequence
        
        Args:
            landmarks_sequence: List of landmarks for each frame
            frame_width: Frame width for scaling sway to pixels
            
        Returns:
            Dictionary with analysis results
        """
        # Set first valid frame as address position
        for landmarks in landmarks_sequence:
            if landmarks is not None:
                self.set_address_position(landmarks)
                break
        
        results = {
            'sway': [],
            'shoulder_turn': [],
            'hip_turn': [],
            'x_factor': [],
            'shoulder_center': [],
            'hip_center': []
        }
        
        for landmarks in landmarks_sequence:
            results['sway'].append(self.calculate_lateral_sway(landmarks, frame_width))
            results['shoulder_turn'].append(self.calculate_shoulder_turn(landmarks))
            results['hip_turn'].append(self.calculate_hip_turn(landmarks))
            results['x_factor'].append(self.calculate_x_factor(landmarks))
            results['shoulder_center'].append(self.calculate_shoulder_center(landmarks))
            results['hip_center'].append(self.calculate_hip_center(landmarks))
        
        # Calculate summary stats
        valid_sway = [s for s in results['sway'] if s is not None]
        valid_shoulder = [s for s in results['shoulder_turn'] if s is not None]
        valid_hip = [h for h in results['hip_turn'] if h is not None]
        valid_xfactor = [x for x in results['x_factor'] if x is not None]
        
        results['summary'] = {
            'max_sway_left': min(valid_sway) if valid_sway else None,
            'max_sway_right': max(valid_sway) if valid_sway else None,
            'max_shoulder_turn': max(valid_shoulder) if valid_shoulder else None,
            'max_hip_turn': max(valid_hip) if valid_hip else None,
            'max_x_factor': max(valid_xfactor) if valid_xfactor else None
        }
        
        return results


# Legacy function interface for backwards compatibility
def calculate_lateral_sway(landmarks_sequence):
    """Calculate lateral sway from face-on view"""
    calc = SwayCalculator()
    results = calc.analyze_sequence(landmarks_sequence)
    return results['sway']

def calculate_rotation(landmarks_sequence):
    """Calculate rotation from DTL view"""
    calc = SwayCalculator()
    results = calc.analyze_sequence(landmarks_sequence)
    return results['shoulder_turn']

