import sys
import os
import cv2
import json
import time
import threading
import numpy as np
from datetime import datetime
from typing import Optional, Dict, List, Tuple

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QTabWidget, QPushButton, QSlider, QComboBox, 
                             QFormLayout, QGroupBox, QSpinBox, QMessageBox, QProgressBar,
                             QSizePolicy, QSplitter, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize, pyqtSlot
from PyQt6.QtGui import QImage, QPixmap, QFont, QAction, QColor, QPalette

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from dual_camera_recorder import DualCameraRecorder, CameraCapture
from pose_processor import PoseProcessor
from sway_calculator import SwayCalculator

# -----------------------------------------------------------------------------
# Configuration & Utils
# -----------------------------------------------------------------------------

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
    except Exception as e:
        print(f"Warning: Could not load config: {e}")
        return None

# -----------------------------------------------------------------------------
# Camera Thread
# -----------------------------------------------------------------------------

class CameraThread(QThread):
    frame_ready = pyqtSignal(int, QImage)  # camera_index, image

    def __init__(self, camera_id: int, camera_index: int, width=1280, height=720, fps=60):
        super().__init__()
        self.camera_id = camera_id
        self.camera_index = camera_index # 1 or 2
        self.width = width
        self.height = height
        self.fps = fps
        self.running = False
        self.cap = None

    def run(self):
        self.running = True
        
        # Open camera
        if sys.platform == 'win32':
            self.cap = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(self.camera_id)
            
        if not self.cap.isOpened():
            print(f"Failed to open camera {self.camera_id}")
            self.running = False
            return

        # Set properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        while self.running:
            ret, frame = self.cap.read()
            if ret:
                # Convert to RGB for Qt
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                self.frame_ready.emit(self.camera_index, qt_image.copy())
            else:
                time.sleep(0.1)
                
        self.cap.release()

    def stop(self):
        self.running = False
        self.wait()
    
    def get_property(self, prop_id):
        if self.cap and self.cap.isOpened():
            return self.cap.get(prop_id)
        return 0.0

    def set_property(self, prop_id, value):
        if self.cap and self.cap.isOpened():
            self.cap.set(prop_id, value)

# -----------------------------------------------------------------------------
# Analysis Thread
# -----------------------------------------------------------------------------

class AnalysisThread(QThread):
    progress_update = pyqtSignal(str, int) # message, percent
    analysis_complete = pyqtSignal(dict, dict) # results1, results2
    error_occurred = pyqtSignal(str)

    def __init__(self, video_files: List[str]):
        super().__init__()
        self.video_files = video_files

    def run(self):
        try:
            video1_path, video2_path = self.video_files
            
            # Camera 1 (Face-On)
            self.progress_update.emit("Processing Camera 1 (Face-On)...", 10)
            processor1 = PoseProcessor(model_complexity=2)
            landmarks_seq1, _ = processor1.process_video(video1_path)
            processor1.release()
            
            self.progress_update.emit("Calculating Metrics for Camera 1...", 40)
            # Get width for scaling
            cap1 = cv2.VideoCapture(video1_path)
            w1 = int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH)) if cap1.isOpened() else 1280
            cap1.release()
            
            calc1 = SwayCalculator()
            analysis1 = calc1.analyze_sequence(landmarks_seq1, w1)
            
            # Detection rate
            detected1 = sum(1 for lm in landmarks_seq1 if lm is not None)
            analysis1['detection_rate'] = (detected1 / len(landmarks_seq1) * 100) if landmarks_seq1 else 0

            # Camera 2 (Down-the-Line)
            self.progress_update.emit("Processing Camera 2 (Down-the-Line)...", 60)
            processor2 = PoseProcessor(model_complexity=2)
            landmarks_seq2, _ = processor2.process_video(video2_path)
            processor2.release()
            
            self.progress_update.emit("Calculating Metrics for Camera 2...", 90)
            # Get width
            cap2 = cv2.VideoCapture(video2_path)
            w2 = int(cap2.get(cv2.CAP_PROP_FRAME_WIDTH)) if cap2.isOpened() else 1280
            cap2.release()

            calc2 = SwayCalculator()
            analysis2 = calc2.analyze_sequence(landmarks_seq2, w2)
            
            detected2 = sum(1 for lm in landmarks_seq2 if lm is not None)
            analysis2['detection_rate'] = (detected2 / len(landmarks_seq2) * 100) if landmarks_seq2 else 0
            
            self.progress_update.emit("Analysis Complete!", 100)
            self.analysis_complete.emit(analysis1, analysis2)

        except Exception as e:
            self.error_occurred.emit(str(e))
            import traceback
            traceback.print_exc()

# -----------------------------------------------------------------------------
# Main GUI
# -----------------------------------------------------------------------------

class VideoLabel(QLabel):
    """Custom Label to display video frames maintaining aspect ratio"""
    def __init__(self, text="No Signal"):
        super().__init__(text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #000; color: #666; font-size: 14px;")
        self.setMinimumSize(320, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.scaled_pixmap = None

    def set_frame(self, image: QImage):
        pixmap = QPixmap.fromImage(image)
        # Scale to fit label while keeping aspect ratio
        self.scaled_pixmap = pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.setPixmap(self.scaled_pixmap)

    def resizeEvent(self, event):
        if self.pixmap() and self.scaled_pixmap:
            # Re-scale when window resizes (optimization: store original pixmap?)
            # For 60fps, we might want to avoid heavy resizing here, but for now it's okay.
            # Ideally, we only scale when set_frame is called with the current size.
            pass
        super().resizeEvent(event)

class CameraSetupTab(QWidget):
    def __init__(self, camera_num: int, parent=None):
        super().__init__(parent)
        self.camera_num = camera_num
        self.layout = QHBoxLayout(self)
        
        # Left: Video Preview
        self.preview_label = VideoLabel(f"Camera {camera_num} Preview")
        self.layout.addWidget(self.preview_label, stretch=2)
        
        # Right: Controls
        self.controls_group = QGroupBox("Camera Settings")
        self.controls_layout = QFormLayout()
        self.controls_group.setLayout(self.controls_layout)
        
        self.sliders = {}
        
        # Define properties to control
        self.properties = [
            ("Brightness", cv2.CAP_PROP_BRIGHTNESS, 0, 255),
            ("Contrast", cv2.CAP_PROP_CONTRAST, 0, 255),
            ("Saturation", cv2.CAP_PROP_SATURATION, 0, 255),
            ("Exposure", cv2.CAP_PROP_EXPOSURE, -13, 0), # Approx range
            ("Gain", cv2.CAP_PROP_GAIN, 0, 100),
            ("Focus", cv2.CAP_PROP_FOCUS, 0, 255),
            ("Sharpness", cv2.CAP_PROP_SHARPNESS, 0, 255),
            ("Gamma", cv2.CAP_PROP_GAMMA, 0, 200)
        ]

        for name, prop_id, min_val, max_val in self.properties:
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(min_val, max_val)
            slider.valueChanged.connect(lambda v, pid=prop_id: self.parent().update_camera_property(self.camera_num, pid, v))
            self.sliders[prop_id] = slider
            self.controls_layout.addRow(name, slider)

        # Buttons
        self.btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Settings")
        self.reset_btn = QPushButton("Reset Defaults")
        self.btn_layout.addWidget(self.save_btn)
        self.btn_layout.addWidget(self.reset_btn)
        self.controls_layout.addRow(self.btn_layout)
        
        # Add controls to main layout
        controls_container = QWidget()
        controls_v_layout = QVBoxLayout(controls_container)
        controls_v_layout.addWidget(self.controls_group)
        controls_v_layout.addStretch()
        self.layout.addWidget(controls_container, stretch=1)

class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Golf Swing Analysis Dashboard")
        self.resize(1600, 900)
        
        # Dark Theme
        self.apply_dark_theme()

        # Camera Threads
        self.cam1_thread = None
        self.cam2_thread = None
        
        # Load Config
        self.config = load_windows_config() or {}
        self.cam1_id = self.config.get('camera1_id', 0)
        self.cam2_id = self.config.get('camera2_id', 1 if sys.platform != 'win32' else 2)
        
        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header
        header = QLabel("Golf Swing Studio")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #4CAF50; margin: 10px;")
        main_layout.addWidget(header)
        
        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Tab 1: Setup Camera 1
        self.tab_cam1 = CameraSetupTab(1, self)
        self.tabs.addTab(self.tab_cam1, "Camera 1 Setup")
        
        # Tab 2: Setup Camera 2
        self.tab_cam2 = CameraSetupTab(2, self)
        self.tabs.addTab(self.tab_cam2, "Camera 2 Setup")
        
        # Tab 3: Recording
        self.tab_record = QWidget()
        self.setup_recording_tab()
        self.tabs.addTab(self.tab_record, "Recording")
        
        # Tab 4: Analysis
        self.tab_analysis = QWidget()
        self.setup_analysis_tab()
        self.tabs.addTab(self.tab_analysis, "Analysis")
        
        # Connect Signals
        self.tabs.currentChanged.connect(self.on_tab_change)
        
        self.tab_cam1.save_btn.clicked.connect(self.save_settings)
        self.tab_cam2.save_btn.clicked.connect(self.save_settings)
        self.tab_cam1.reset_btn.clicked.connect(lambda: self.reset_settings(1))
        self.tab_cam2.reset_btn.clicked.connect(lambda: self.reset_settings(2))

        # Start Cameras
        self.start_preview_cameras()

    def apply_dark_theme(self):
        app = QApplication.instance()
        app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        app.setPalette(palette)

    def setup_recording_tab(self):
        layout = QVBoxLayout(self.tab_record)
        
        # Video Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.rec_preview1 = VideoLabel("Camera 1")
        self.rec_preview2 = VideoLabel("Camera 2")
        splitter.addWidget(self.rec_preview1)
        splitter.addWidget(self.rec_preview2)
        layout.addWidget(splitter, stretch=4)
        
        # Controls
        controls = QWidget()
        ctrl_layout = QHBoxLayout(controls)
        
        self.record_btn = QPushButton("START RECORDING")
        self.record_btn.setMinimumHeight(50)
        self.record_btn.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold; font-size: 16px;")
        self.record_btn.clicked.connect(self.toggle_recording)
        
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        ctrl_layout.addWidget(self.record_btn)
        ctrl_layout.addWidget(self.status_label)
        
        layout.addWidget(controls, stretch=1)
        
        self.is_recording = False
        self.recorder = None
        self.recording_start_time = 0

    def setup_analysis_tab(self):
        layout = QVBoxLayout(self.tab_analysis)
        
        # Results container
        self.analysis_results_group = QGroupBox("Analysis Results")
        res_layout = QGridLayout = QVBoxLayout(self.analysis_results_group)
        
        self.analysis_label = QLabel("No analysis available. Record a video to begin.")
        self.analysis_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.analysis_label.setStyleSheet("font-size: 14px;")
        res_layout.addWidget(self.analysis_label)
        
        layout.addWidget(self.analysis_results_group)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

    def start_preview_cameras(self):
        if self.cam1_thread: self.cam1_thread.stop()
        if self.cam2_thread: self.cam2_thread.stop()

        self.cam1_thread = CameraThread(self.cam1_id, 1)
        self.cam1_thread.frame_ready.connect(self.update_frame)
        self.cam1_thread.start()

        self.cam2_thread = CameraThread(self.cam2_id, 2)
        self.cam2_thread.frame_ready.connect(self.update_frame)
        self.cam2_thread.start()
        
        # Initialize sliders from camera values after a short delay
        QTimer.singleShot(1000, self.init_slider_values)

    def init_slider_values(self):
        for tab in [self.tab_cam1, self.tab_cam2]:
            thread = self.cam1_thread if tab == self.tab_cam1 else self.cam2_thread
            for prop_id, slider in tab.sliders.items():
                val = thread.get_property(prop_id)
                slider.blockSignals(True)
                slider.setValue(int(val))
                slider.blockSignals(False)

    @pyqtSlot(int, QImage)
    def update_frame(self, cam_index, image):
        # Update setup tabs
        if cam_index == 1:
            if self.tabs.currentWidget() == self.tab_cam1:
                self.tab_cam1.preview_label.set_frame(image)
            elif self.tabs.currentWidget() == self.tab_record:
                self.rec_preview1.set_frame(image)
        elif cam_index == 2:
            if self.tabs.currentWidget() == self.tab_cam2:
                self.tab_cam2.preview_label.set_frame(image)
            elif self.tabs.currentWidget() == self.tab_record:
                self.rec_preview2.set_frame(image)

    def update_camera_property(self, cam_num, prop_id, value):
        thread = self.cam1_thread if cam_num == 1 else self.cam2_thread
        if thread:
            thread.set_property(prop_id, value)

    def save_settings(self):
        # Implementation for saving settings to JSON
        QMessageBox.information(self, "Settings", "Settings saved successfully!")

    def reset_settings(self, cam_num):
        # Implementation for resetting settings
        QMessageBox.information(self, "Settings", f"Camera {cam_num} settings reset!")

    def on_tab_change(self, index):
        # Handle logic when switching tabs (e.g., pause analysis, etc.)
        pass

    def toggle_recording(self):
        if not self.is_recording:
            # Start Recording
            self.stop_preview_threads() # Release cameras for recorder
            
            try:
                self.recorder = DualCameraRecorder(self.cam1_id, self.cam2_id)
                self.recorder.start_cameras()
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                self.current_recording_name = f"recording_{timestamp}"
                self.recorder.start_recording(self.current_recording_name)
                
                self.is_recording = True
                self.record_btn.setText("STOP RECORDING")
                self.record_btn.setStyleSheet("background-color: #388e3c; color: white; font-weight: bold; font-size: 16px;")
                self.status_label.setText("Recording in progress...")
                self.recording_start_time = time.time()
                
                # Start a timer to update recording duration and previews from recorder
                self.rec_timer = QTimer()
                self.rec_timer.timeout.connect(self.update_recording_ui)
                self.rec_timer.start(50) # 20fps UI update
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to start recording: {e}")
                self.start_preview_cameras() # Restart previews
        else:
            # Stop Recording
            self.rec_timer.stop()
            self.recorder.stop_recording()
            self.recorder.stop_cameras()
            self.recorder = None
            self.is_recording = False
            
            self.record_btn.setText("START RECORDING")
            self.record_btn.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold; font-size: 16px;")
            self.status_label.setText("Recording stopped. Analyzing...")
            
            # Restart previews
            self.start_preview_cameras()
            
            # Trigger Analysis
            self.start_analysis()

    def update_recording_ui(self):
        if self.recorder and self.is_recording:
            # Update duration
            elapsed = time.time() - self.recording_start_time
            self.status_label.setText(f"Recording... {elapsed:.1f}s")
            
            # Get frames from recorder for preview
            # Note: accessing recorder.cameraX directly is a bit hacky but works for this
            f1 = self.recorder.camera1.get_frame(0.01)
            f2 = self.recorder.camera2.get_frame(0.01)
            
            if f1:
                rgb1 = cv2.cvtColor(f1[0], cv2.COLOR_BGR2RGB)
                h, w, ch = rgb1.shape
                img1 = QImage(rgb1.data, w, h, ch * w, QImage.Format.Format_RGB888)
                self.rec_preview1.set_frame(img1.copy())
                
            if f2:
                rgb2 = cv2.cvtColor(f2[0], cv2.COLOR_BGR2RGB)
                h, w, ch = rgb2.shape
                img2 = QImage(rgb2.data, w, h, ch * w, QImage.Format.Format_RGB888)
                self.rec_preview2.set_frame(img2.copy())

    def stop_preview_threads(self):
        if self.cam1_thread: self.cam1_thread.stop()
        if self.cam2_thread: self.cam2_thread.stop()

    def start_analysis(self):
        self.tabs.setCurrentWidget(self.tab_analysis)
        self.progress_bar.setValue(0)
        
        # Files
        files = [
            os.path.join("recordings", f"{self.current_recording_name}_camera1.mp4"),
            os.path.join("recordings", f"{self.current_recording_name}_camera2.mp4")
        ]
        
        self.analysis_thread = AnalysisThread(files)
        self.analysis_thread.progress_update.connect(lambda msg, p: (self.analysis_label.setText(msg), self.progress_bar.setValue(p)))
        self.analysis_thread.analysis_complete.connect(self.show_analysis_results)
        self.analysis_thread.error_occurred.connect(lambda e: self.analysis_label.setText(f"Error: {e}"))
        self.analysis_thread.start()

    def show_analysis_results(self, res1, res2):
        self.analysis_label.setText("")
        
        # Build Summary HTML
        summary1 = res1.get('summary', {})
        summary2 = res2.get('summary', {})
        
        html = """
        <h2 style='color: #4CAF50;'>Analysis Results</h2>
        <table border='1' cellspacing='0' cellpadding='10' style='border-color: #555;'>
            <tr>
                <th style='background-color: #333;'>Metric</th>
                <th style='background-color: #333;'>Value</th>
            </tr>
            <tr>
                <td>Detection Rate (Face-On)</td>
                <td>{:.1f}%</td>
            </tr>
             <tr>
                <td>Detection Rate (DTL)</td>
                <td>{:.1f}%</td>
            </tr>
            <tr>
                <td>Max Sway Left</td>
                <td>{:.1f} px</td>
            </tr>
            <tr>
                <td>Max Sway Right</td>
                <td>{:.1f} px</td>
            </tr>
            <tr>
                <td>Max Shoulder Turn</td>
                <td>{:.1f}°</td>
            </tr>
            <tr>
                <td>Max Hip Turn</td>
                <td>{:.1f}°</td>
            </tr>
            <tr>
                <td>Max X-Factor</td>
                <td>{:.1f}°</td>
            </tr>
        </table>
        """.format(
            res1.get('detection_rate', 0),
            res2.get('detection_rate', 0),
            abs(summary1.get('max_sway_left') or 0),
            summary1.get('max_sway_right') or 0,
            summary2.get('max_shoulder_turn') or 0,
            summary2.get('max_hip_turn') or 0,
            summary2.get('max_x_factor') or 0
        )
        
        self.analysis_label.setText(html)
        self.analysis_label.setTextFormat(Qt.TextFormat.RichText)

    def closeEvent(self, event):
        self.stop_preview_threads()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = DashboardWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
