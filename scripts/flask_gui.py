"""
Flask-based Camera Setup & Recording GUI

Replaces the OpenCV highgui-based GUI with a web interface.
Eliminates font rendering issues by leveraging browser-native text rendering.
Target: 120fps dual camera recording with real-time preview.

Usage:
    python scripts/flask_gui.py [--camera1 0] [--camera2 1] [--fps 120] [--port 5000]

Then open http://localhost:5000 in your browser.
"""

import cv2
import sys
import os
import json
import threading
import time
import numpy as np
from typing import Optional, Tuple, Dict
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from dual_camera_recorder import DualCameraRecorder
from pose_processor import PoseProcessor
from sway_calculator import SwayCalculator

from flask import Flask, render_template, jsonify, request, Response


def load_windows_config(config_path: str = None) -> dict:
    """Load Windows-specific camera configuration from JSON file"""
    if config_path is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(project_root, 'config_windows.json')

    if not os.path.exists(config_path):
        return None

    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load config from {config_path}: {e}")
        return None


class CameraManager:
    """Manages camera state, recording, and analysis for the Flask GUI.

    This replaces TabbedCameraGUI's state management while keeping
    the same recording and analysis pipeline.
    """

    # OpenCV camera property constants
    PROP_MAP = {
        'brightness': cv2.CAP_PROP_BRIGHTNESS,
        'contrast': cv2.CAP_PROP_CONTRAST,
        'saturation': cv2.CAP_PROP_SATURATION,
        'exposure': cv2.CAP_PROP_EXPOSURE,
        'gain': cv2.CAP_PROP_GAIN,
        'focus': cv2.CAP_PROP_FOCUS,
        'white_balance': cv2.CAP_PROP_WHITE_BALANCE_BLUE_U,
        'sharpness': cv2.CAP_PROP_SHARPNESS,
        'gamma': cv2.CAP_PROP_GAMMA,
    }

    PROP_RANGES = {
        'brightness': {'min': 0, 'max': 255, 'default': 128, 'step': 1},
        'contrast': {'min': 0, 'max': 255, 'default': 32, 'step': 1},
        'saturation': {'min': 0, 'max': 255, 'default': 64, 'step': 1},
        'exposure': {'min': -13, 'max': 1, 'default': -6, 'step': 0.5},
        'gain': {'min': 0, 'max': 100, 'default': 0, 'step': 1},
        'focus': {'min': 0, 'max': 255, 'default': 0, 'step': 1},
        'white_balance': {'min': 2000, 'max': 6500, 'default': 4000, 'step': 100},
        'sharpness': {'min': 0, 'max': 255, 'default': 0, 'step': 1},
        'gamma': {'min': 0, 'max': 200, 'default': 100, 'step': 1},
    }

    # Tab names (mirrors the original GUI)
    TAB_NAMES = ["Camera 1 Setup", "Camera 2 Setup", "Recording", "Analysis"]

    def __init__(self, camera1_id: int = None, camera2_id: int = None,
                 width: int = 1280, height: int = 720, fps: int = 120):
        # Determine camera IDs by platform
        if sys.platform == 'win32':
            config = load_windows_config()
            if config:
                if camera1_id is None:
                    camera1_id = config.get('camera1_id', 0)
                if camera2_id is None:
                    camera2_id = config.get('camera2_id', 2)
            self.camera1_id = camera1_id if camera1_id is not None else 0
            self.camera2_id = camera2_id if camera2_id is not None else 2
        else:
            self.camera1_id = camera1_id if camera1_id is not None else 0
            self.camera2_id = camera2_id if camera2_id is not None else 1

        self.width = width
        self.height = height
        self.fps = fps

        # Camera state
        self.cap1 = None
        self.cap2 = None
        self.cameras_available = False
        self.running = False

        # Frame buffers (shared between capture thread and MJPEG streams)
        self.latest_frame1 = None
        self.latest_frame2 = None
        self.frame_lock = threading.Lock()
        self.capture_thread = None

        # Recording state
        self.recorder = None
        self.is_recording = False
        self.recording_start_time = None
        self.recording_files = None

        # Analysis state
        self.is_analyzing = False
        self.analysis_progress = ""
        self.analysis_start_time = None
        self.analysis_camera1 = None
        self.analysis_camera2 = None
        self.analysis_frame_index = 0

        # Status messages
        self.status_message = ""
        self.status_time = 0

    # ------------------------------------------------------------------
    # Camera lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """Initialize cameras and start background capture thread."""
        print(f"Starting cameras: cam1={self.camera1_id}, cam2={self.camera2_id}")
        print(f"Resolution: {self.width}x{self.height} @ {self.fps}fps (120fps recording target)")

        if sys.platform == 'win32':
            self.cap1 = cv2.VideoCapture(self.camera1_id, cv2.CAP_DSHOW)
            self.cap2 = cv2.VideoCapture(self.camera2_id, cv2.CAP_DSHOW)
        else:
            self.cap1 = cv2.VideoCapture(self.camera1_id)
            self.cap2 = cv2.VideoCapture(self.camera2_id)

        cam1_ok = self.cap1.isOpened() if self.cap1 else False
        cam2_ok = self.cap2.isOpened() if self.cap2 else False
        self.cameras_available = cam1_ok and cam2_ok

        if not cam1_ok:
            print(f"WARNING: Camera 1 (ID: {self.camera1_id}) not available")
            if self.cap1:
                try:
                    self.cap1.release()
                except Exception:
                    pass
            self.cap1 = None

        if not cam2_ok:
            print(f"WARNING: Camera 2 (ID: {self.camera2_id}) not available")
            if self.cap2:
                try:
                    self.cap2.release()
                except Exception:
                    pass
            self.cap2 = None

        # Configure cameras
        for cap in [self.cap1, self.cap2]:
            if cap and cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                cap.set(cv2.CAP_PROP_FPS, self.fps)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Print actual camera info
        for cam_num, cap in [(1, self.cap1), (2, self.cap2)]:
            if cap and cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                f = cap.get(cv2.CAP_PROP_FPS)
                print(f"Camera {cam_num}: {w}x{h} @ {f:.1f}fps")
            else:
                print(f"Camera {cam_num}: Not available")

        # Start background capture thread
        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

        print("Camera manager started")

    def _capture_loop(self):
        """Background thread that continuously grabs frames from both cameras."""
        while self.running:
            if self.is_recording:
                # Cameras are owned by the recorder during recording
                time.sleep(0.1)
                continue

            if self.cap1 and self.cap1.isOpened():
                ret, frame = self.cap1.read()
                if ret:
                    with self.frame_lock:
                        self.latest_frame1 = frame

            if self.cap2 and self.cap2.isOpened():
                ret, frame = self.cap2.read()
                if ret:
                    with self.frame_lock:
                        self.latest_frame2 = frame

            time.sleep(1.0 / 60)  # capture at ~60fps for smooth preview

    def get_frame(self, camera_num: int) -> Optional[np.ndarray]:
        """Return the latest frame for the given camera (thread-safe copy)."""
        with self.frame_lock:
            if camera_num == 1 and self.latest_frame1 is not None:
                return self.latest_frame1.copy()
            elif camera_num == 2 and self.latest_frame2 is not None:
                return self.latest_frame2.copy()
        return None

    # ------------------------------------------------------------------
    # Camera properties
    # ------------------------------------------------------------------

    def get_camera_properties(self, camera_num: int) -> Optional[Dict]:
        """Get all current property values + ranges for a camera."""
        cap = self.cap1 if camera_num == 1 else self.cap2
        if not cap or not cap.isOpened():
            return None

        props = {}
        for name, cv_prop in self.PROP_MAP.items():
            props[name] = {
                'value': cap.get(cv_prop),
                **self.PROP_RANGES[name],
            }

        props['_info'] = {
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': cap.get(cv2.CAP_PROP_FPS),
        }
        return props

    def set_camera_property(self, camera_num: int, prop_name: str, value) -> bool:
        """Set a single camera property."""
        cap = self.cap1 if camera_num == 1 else self.cap2
        if not cap or not cap.isOpened():
            return False
        if prop_name not in self.PROP_MAP:
            return False
        cap.set(self.PROP_MAP[prop_name], float(value))
        return True

    def reset_camera_properties(self, camera_num: int) -> bool:
        """Reset all camera properties to their defaults."""
        cap = self.cap1 if camera_num == 1 else self.cap2
        if not cap or not cap.isOpened():
            return False
        for name, cv_prop in self.PROP_MAP.items():
            cap.set(cv_prop, self.PROP_RANGES[name]['default'])
        return True

    def save_settings(self) -> Optional[str]:
        """Persist current camera settings to a timestamped JSON file."""
        settings = {}
        for cam_num in [1, 2]:
            cap = self.cap1 if cam_num == 1 else self.cap2
            if cap and cap.isOpened():
                settings[f'camera{cam_num}'] = {
                    name: float(cap.get(cv_prop))
                    for name, cv_prop in self.PROP_MAP.items()
                }

        filename = f"camera_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.join(project_root, filename)

        try:
            with open(filepath, 'w') as f:
                json.dump(settings, f, indent=2)
            self.status_message = f"Settings saved: {filename}"
            self.status_time = time.time()
            print(f"Settings saved to {filepath}")
            return filename
        except Exception as e:
            self.status_message = f"Failed to save: {e}"
            self.status_time = time.time()
            return None

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def start_recording(self) -> Dict:
        """Start dual camera 120fps recording."""
        if self.is_recording:
            return {'error': 'Already recording'}

        if not self.cameras_available:
            self.status_message = "Cameras not available - cannot record"
            self.status_time = time.time()
            return {'error': 'Cameras not available'}

        if not (self.cap1 and self.cap1.isOpened() and self.cap2 and self.cap2.isOpened()):
            self.status_message = "Cameras not available - cannot record"
            self.status_time = time.time()
            return {'error': 'Camera state mismatch'}

        try:
            # Save current camera settings before releasing
            cam1_settings = {}
            cam2_settings = {}
            if self.cap1 and self.cap1.isOpened():
                for cv_prop in self.PROP_MAP.values():
                    cam1_settings[cv_prop] = self.cap1.get(cv_prop)
            if self.cap2 and self.cap2.isOpened():
                for cv_prop in self.PROP_MAP.values():
                    cam2_settings[cv_prop] = self.cap2.get(cv_prop)

            # Release preview cameras so the recorder can claim them
            for cap in [self.cap1, self.cap2]:
                if cap and cap.isOpened():
                    try:
                        cap.release()
                    except Exception:
                        pass

            # Clear frame buffers
            with self.frame_lock:
                self.latest_frame1 = None
                self.latest_frame2 = None

            # Create and start the recorder (120fps target)
            self.recorder = DualCameraRecorder(
                camera1_id=self.camera1_id,
                camera2_id=self.camera2_id,
            )
            self.recorder.start_cameras(width=self.width, height=self.height, fps=self.fps)

            # Re-apply camera settings to the recorder's cameras
            for cv_prop, value in cam1_settings.items():
                try:
                    self.recorder.camera1.cap.set(cv_prop, value)
                except Exception:
                    pass
            for cv_prop, value in cam2_settings.items():
                try:
                    self.recorder.camera2.cap.set(cv_prop, value)
                except Exception:
                    pass

            # Generate output filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"recording_{timestamp}"
            self.recorder.start_recording(filename)

            self.is_recording = True
            self.recording_start_time = time.time()
            self.recording_files = [
                os.path.join(self.recorder.output_dir, f"{filename}_camera1.mp4"),
                os.path.join(self.recorder.output_dir, f"{filename}_camera2.mp4"),
            ]

            self.status_message = "Recording started"
            self.status_time = time.time()
            print(f"Recording started: {filename} @ {self.fps}fps")
            return {'success': True, 'filename': filename}

        except Exception as e:
            self.is_recording = False
            if self.recorder:
                try:
                    self.recorder.stop_cameras()
                except Exception:
                    pass
                self.recorder = None
            self._reopen_cameras()
            self.status_message = f"Recording error: {e}"
            self.status_time = time.time()
            return {'error': str(e)}

    def stop_recording(self) -> Dict:
        """Stop recording, reopen preview cameras, trigger analysis."""
        if not self.is_recording:
            return {'error': 'Not recording'}

        if not self.recorder:
            self.is_recording = False
            return {'error': 'No active recorder'}

        try:
            self.recorder.stop_recording()
            self.recorder.stop_cameras()
            self.is_recording = False

            duration = (time.time() - self.recording_start_time) if self.recording_start_time else 0
            self.status_message = f"Recording stopped ({duration:.1f}s)"
            self.status_time = time.time()
            self.recording_start_time = None

            print(f"Recording stopped. Duration: {duration:.1f}s")
            if self.recording_files:
                for f in self.recording_files:
                    print(f"  {f}")

            time.sleep(0.5)
            self._reopen_cameras()
            time.sleep(0.5)
            self.recorder = None

            # Auto-start analysis
            if self.recording_files and len(self.recording_files) == 2:
                self.start_analysis()

            return {'success': True, 'duration': duration}

        except Exception as e:
            self.is_recording = False
            if self.recorder:
                try:
                    self.recorder.stop_cameras()
                except Exception:
                    pass
            self.recorder = None
            self._reopen_cameras()
            self.status_message = f"Error stopping: {e}"
            self.status_time = time.time()
            return {'error': str(e)}

    def _reopen_cameras(self):
        """Re-open cameras for preview after recording finishes."""
        if not self.cameras_available:
            return
        try:
            if sys.platform == 'win32':
                self.cap1 = cv2.VideoCapture(self.camera1_id, cv2.CAP_DSHOW)
                self.cap2 = cv2.VideoCapture(self.camera2_id, cv2.CAP_DSHOW)
            else:
                self.cap1 = cv2.VideoCapture(self.camera1_id)
                self.cap2 = cv2.VideoCapture(self.camera2_id)

            for cap in [self.cap1, self.cap2]:
                if cap and cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    cap.set(cv2.CAP_PROP_FPS, self.fps)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                else:
                    print("WARNING: Failed to reopen a camera after recording")
        except Exception as e:
            print(f"Error reopening cameras: {e}")
            self.cap1 = None
            self.cap2 = None

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def start_analysis(self):
        """Kick off pose analysis of the most recent recording."""
        if self.is_analyzing:
            return
        if not self.recording_files or len(self.recording_files) != 2:
            self.status_message = "No videos to analyze"
            self.status_time = time.time()
            return
        if not all(os.path.exists(f) for f in self.recording_files):
            self.status_message = "Video files not found"
            self.status_time = time.time()
            return

        self.is_analyzing = True
        self.analysis_progress = "Starting analysis..."
        self.analysis_start_time = time.time()
        self.analysis_camera1 = None
        self.analysis_camera2 = None
        self.analysis_frame_index = 0

        thread = threading.Thread(target=self._analyze_videos, daemon=True)
        thread.start()

    def _analyze_videos(self):
        """Background thread: run MediaPipe pose analysis on both videos."""
        try:
            video1_path = self.recording_files[0]
            video2_path = self.recording_files[1]
            time.sleep(1.0)  # let video files flush

            if not os.path.exists(video1_path):
                raise FileNotFoundError(f"Not found: {video1_path}")
            if not os.path.exists(video2_path):
                raise FileNotFoundError(f"Not found: {video2_path}")

            # Get video dimensions
            cap = cv2.VideoCapture(video1_path)
            frame_width1 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if cap.isOpened() else 1280
            cap.release()
            cap = cv2.VideoCapture(video2_path)
            frame_width2 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if cap.isOpened() else 1280
            cap.release()

            # --- Camera 1 (face-on) ---
            self.analysis_progress = "Processing Camera 1 (face-on)..."
            processor1 = PoseProcessor(model_complexity=2)
            landmarks1, _ = processor1.process_video(video1_path)
            processor1.release()

            calc1 = SwayCalculator()
            analysis1 = calc1.analyze_sequence(landmarks1, frame_width1)
            detected1 = sum(1 for lm in landmarks1 if lm is not None)
            analysis1['detection_rate'] = (detected1 / len(landmarks1) * 100) if landmarks1 else 0
            self.analysis_camera1 = analysis1

            # --- Camera 2 (down-the-line) ---
            self.analysis_progress = "Processing Camera 2 (down-the-line)..."
            processor2 = PoseProcessor(model_complexity=2)
            landmarks2, _ = processor2.process_video(video2_path)
            processor2.release()

            calc2 = SwayCalculator()
            analysis2 = calc2.analyze_sequence(landmarks2, frame_width2)
            detected2 = sum(1 for lm in landmarks2 if lm is not None)
            analysis2['detection_rate'] = (detected2 / len(landmarks2) * 100) if landmarks2 else 0
            self.analysis_camera2 = analysis2

            self.is_analyzing = False
            self.analysis_progress = ""
            elapsed = time.time() - self.analysis_start_time if self.analysis_start_time else 0
            self.status_message = f"Analysis complete ({elapsed:.1f}s)"
            self.status_time = time.time()
            print(f"Analysis complete in {elapsed:.1f}s")

        except Exception as e:
            self.is_analyzing = False
            self.analysis_progress = ""
            self.status_message = f"Analysis failed: {e}"
            self.status_time = time.time()
            print(f"Analysis error: {e}")
            import traceback
            traceback.print_exc()

    def get_analysis_results(self) -> Dict:
        """Return analysis results formatted for the web UI."""
        if self.analysis_camera1 is None and self.analysis_camera2 is None:
            return {
                'is_analyzing': self.is_analyzing,
                'progress': self.analysis_progress,
                'frame_index': self.analysis_frame_index,
                'max_frames': 0,
                'camera1': None,
                'camera2': None,
            }

        # Determine max frame count
        max_frames = 0
        if self.analysis_camera1:
            max_frames = max(max_frames, len(self.analysis_camera1.get('sway', [])))
        if self.analysis_camera2:
            max_frames = max(max_frames, len(self.analysis_camera2.get('shoulder_turn', [])))

        # Clamp frame index *before* building results
        if max_frames > 0:
            self.analysis_frame_index = max(0, min(max_frames - 1, self.analysis_frame_index))
        frame_idx = self.analysis_frame_index

        results = {
            'is_analyzing': self.is_analyzing,
            'progress': self.analysis_progress,
            'frame_index': self.analysis_frame_index,
            'max_frames': max_frames,
            'camera1': None,
            'camera2': None,
        }

        # Camera 1 results
        if self.analysis_camera1:
            summary1 = self.analysis_camera1.get('summary', {})
            current_sway = None
            sway_list = self.analysis_camera1.get('sway', [])
            if frame_idx < len(sway_list):
                current_sway = sway_list[frame_idx]
            results['camera1'] = {
                'summary': summary1,
                'detection_rate': self.analysis_camera1.get('detection_rate', 0),
                'current': {'sway': current_sway},
            }

        # Camera 2 results
        if self.analysis_camera2:
            summary2 = self.analysis_camera2.get('summary', {})
            shoulder_list = self.analysis_camera2.get('shoulder_turn', [])
            hip_list = self.analysis_camera2.get('hip_turn', [])
            xfactor_list = self.analysis_camera2.get('x_factor', [])
            results['camera2'] = {
                'summary': summary2,
                'detection_rate': self.analysis_camera2.get('detection_rate', 0),
                'current': {
                    'shoulder_turn': shoulder_list[frame_idx] if frame_idx < len(shoulder_list) else None,
                    'hip_turn': hip_list[frame_idx] if frame_idx < len(hip_list) else None,
                    'x_factor': xfactor_list[frame_idx] if frame_idx < len(xfactor_list) else None,
                },
            }

        return results

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def stop(self):
        """Release all resources."""
        self.running = False

        if self.is_recording:
            try:
                self.stop_recording()
            except Exception:
                pass

        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)

        for cap in [self.cap1, self.cap2]:
            if cap:
                try:
                    cap.release()
                except Exception:
                    pass

        print("Camera manager stopped")


# ======================================================================
# Flask application
# ======================================================================

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(_project_root, 'templates'),
    static_folder=os.path.join(_project_root, 'static'),
)

# Global singleton - set in main() or by tests
camera_manager: Optional[CameraManager] = None


def get_manager() -> Optional[CameraManager]:
    """Return the global CameraManager instance."""
    global camera_manager
    return camera_manager


# ------------------------------------------------------------------
# MJPEG streaming
# ------------------------------------------------------------------

def _placeholder_jpeg(text: str, color=(0, 200, 200)) -> bytes:
    """Create a placeholder JPEG with the given message."""
    img = np.zeros((360, 640, 3), dtype=np.uint8)
    cv2.putText(img, text, (40, 180),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    _, buf = cv2.imencode('.jpg', img)
    return buf.tobytes()


def generate_frames(camera_num: int):
    """Generator yielding MJPEG frames for a camera stream."""
    while True:
        mgr = get_manager()
        if mgr is None:
            frame_bytes = _placeholder_jpeg("Initializing...")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(1.0)
            continue

        if mgr.is_recording:
            frame_bytes = _placeholder_jpeg("Recording in progress...")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.5)
            continue

        frame = mgr.get_frame(camera_num)
        if frame is not None:
            _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
        else:
            frame_bytes = _placeholder_jpeg(f"Camera {camera_num} not available", (0, 0, 255))
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.5)
            continue

        time.sleep(1.0 / 30)  # ~30fps preview in browser


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.route('/')
def index():
    """Serve the main single-page UI."""
    return render_template('index.html')


@app.route('/video_feed/<int:camera_num>')
def video_feed(camera_num):
    """MJPEG stream endpoint for live camera preview."""
    return Response(generate_frames(camera_num),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/status')
def api_status():
    """Overall system status (polled by the UI)."""
    mgr = get_manager()
    if mgr is None:
        return jsonify({'error': 'Not initialized'})

    return jsonify({
        'cameras_available': mgr.cameras_available,
        'is_recording': mgr.is_recording,
        'is_analyzing': mgr.is_analyzing,
        'analysis_progress': mgr.analysis_progress,
        'recording_duration': (time.time() - mgr.recording_start_time) if mgr.recording_start_time else 0,
        'recording_files': [os.path.basename(f) for f in mgr.recording_files] if mgr.recording_files else [],
        'status_message': mgr.status_message,
        'fps': mgr.fps,
        'width': mgr.width,
        'height': mgr.height,
    })


@app.route('/api/camera/<int:camera_num>/properties')
def api_camera_properties(camera_num):
    """Get all camera property values and ranges."""
    mgr = get_manager()
    if mgr is None:
        return jsonify({'error': 'Not initialized'})
    props = mgr.get_camera_properties(camera_num)
    if props is None:
        return jsonify({'error': f'Camera {camera_num} not available'})
    return jsonify(props)


@app.route('/api/camera/<int:camera_num>/property', methods=['POST'])
def api_set_camera_property(camera_num):
    """Set a single camera property."""
    mgr = get_manager()
    if mgr is None:
        return jsonify({'error': 'Not initialized'})
    data = request.get_json()
    if not data or 'name' not in data or 'value' not in data:
        return jsonify({'error': 'Missing name or value'}), 400
    ok = mgr.set_camera_property(camera_num, data['name'], data['value'])
    return jsonify({'success': ok})


@app.route('/api/camera/<int:camera_num>/reset', methods=['POST'])
def api_reset_camera(camera_num):
    """Reset camera properties to defaults."""
    mgr = get_manager()
    if mgr is None:
        return jsonify({'error': 'Not initialized'})
    ok = mgr.reset_camera_properties(camera_num)
    return jsonify({'success': ok})


@app.route('/api/settings/save', methods=['POST'])
def api_save_settings():
    """Save camera settings to a JSON file."""
    mgr = get_manager()
    if mgr is None:
        return jsonify({'error': 'Not initialized'})
    filename = mgr.save_settings()
    if filename:
        return jsonify({'success': True, 'filename': filename})
    return jsonify({'error': 'Failed to save'})


@app.route('/api/recording/start', methods=['POST'])
def api_start_recording():
    """Start 120fps dual camera recording."""
    mgr = get_manager()
    if mgr is None:
        return jsonify({'error': 'Not initialized'})
    return jsonify(mgr.start_recording())


@app.route('/api/recording/stop', methods=['POST'])
def api_stop_recording():
    """Stop recording, trigger analysis."""
    mgr = get_manager()
    if mgr is None:
        return jsonify({'error': 'Not initialized'})
    return jsonify(mgr.stop_recording())


@app.route('/api/analysis/results')
def api_analysis_results():
    """Get current analysis results and frame data."""
    mgr = get_manager()
    if mgr is None:
        return jsonify({'error': 'Not initialized'})
    return jsonify(mgr.get_analysis_results())


@app.route('/api/analysis/frame', methods=['POST'])
def api_set_analysis_frame():
    """Set the current analysis frame index."""
    mgr = get_manager()
    if mgr is None:
        return jsonify({'error': 'Not initialized'})
    data = request.get_json()
    if not data or 'index' not in data:
        return jsonify({'error': 'Missing index'}), 400
    mgr.analysis_frame_index = int(data['index'])
    return jsonify(mgr.get_analysis_results())


# ======================================================================
# Main entry point
# ======================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Flask Camera Setup & Recording GUI (120fps target)')
    if sys.platform == 'win32':
        config = load_windows_config()
        if config:
            default_cam1, default_cam2 = config.get('camera1_id', 0), config.get('camera2_id', 2)
        else:
            default_cam1, default_cam2 = 0, 2
    else:
        default_cam1, default_cam2 = 0, 1

    parser.add_argument('--camera1', type=int, default=default_cam1,
                        help=f'Camera 1 ID (default: {default_cam1})')
    parser.add_argument('--camera2', type=int, default=default_cam2,
                        help=f'Camera 2 ID (default: {default_cam2})')
    parser.add_argument('--width', type=int, default=1280, help='Resolution width (default: 1280)')
    parser.add_argument('--height', type=int, default=720, help='Resolution height (default: 720)')
    parser.add_argument('--fps', type=int, default=120, help='Recording FPS target (default: 120)')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Port (default: 5000)')

    args = parser.parse_args()

    global camera_manager
    camera_manager = CameraManager(
        camera1_id=args.camera1,
        camera2_id=args.camera2,
        width=args.width,
        height=args.height,
        fps=args.fps,
    )
    camera_manager.start()

    print()
    print("=" * 60)
    print(f"  Flask GUI running at http://localhost:{args.port}")
    print(f"  Recording target: {args.fps}fps @ {args.width}x{args.height}")
    print(f"  Press Ctrl+C to stop")
    print("=" * 60)
    print()

    try:
        app.run(host=args.host, port=args.port, threaded=True, debug=False)
    finally:
        camera_manager.stop()


if __name__ == '__main__':
    main()
