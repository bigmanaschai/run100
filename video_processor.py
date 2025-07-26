import cv2
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import mediapipe as mp
import math


class VideoProcessor:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils

    def process_video(self, video_path: str, range_offset: float = 0) -> Dict:
        """Process a single video and extract runner data"""
        cap = cv2.VideoCapture(video_path)

        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0

        # Initialize data storage
        positions = []
        velocities = []
        timestamps = []

        # Calibration: pixels to meters conversion
        # Assuming the 25m range is captured in full frame width
        pixels_per_meter = width / 25.0

        prev_position = None
        prev_time = None

        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Current timestamp
            current_time = frame_idx / fps

            # Process frame with MediaPipe
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(frame_rgb)

            if results.pose_landmarks:
                # Get hip center position (average of left and right hip)
                left_hip = results.pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_HIP]
                right_hip = results.pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_HIP]

                # Calculate center position in pixels
                center_x = (left_hip.x + right_hip.x) / 2 * width
                center_y = (left_hip.y + right_hip.y) / 2 * height

                # Convert to meters and add range offset
                position_m = (center_x / pixels_per_meter) + range_offset

                # Store position
                positions.append(position_m)
                timestamps.append(current_time)

                # Calculate velocity
                if prev_position is not None and prev_time is not None:
                    time_diff = current_time - prev_time
                    if time_diff > 0:
                        velocity = (position_m - prev_position) / time_diff
                        velocities.append(abs(velocity))  # Use absolute velocity
                    else:
                        velocities.append(0)
                else:
                    velocities.append(0)

                prev_position = position_m
                prev_time = current_time

            frame_idx += 1

        cap.release()

        # Smooth velocities using moving average
        if len(velocities) > 5:
            velocities = self._smooth_data(velocities, window_size=5)

        # Calculate statistics
        valid_velocities = [v for v in velocities if v > 0 and v < 15]  # Filter outliers

        return {
            'positions': positions,
            'velocities': velocities,
            'timestamps': timestamps,
            'max_speed': max(valid_velocities) if valid_velocities else 0,
            'avg_speed': np.mean(valid_velocities) if valid_velocities else 0,
            'time': duration,
            'fps': fps,
            'resolution': f"{width}x{height}",
            'frame_count': frame_count
        }

    def _smooth_data(self, data: List[float], window_size: int = 5) -> List[float]:
        """Apply moving average smoothing to data"""
        smoothed = []
        half_window = window_size // 2

        for i in range(len(data)):
            start = max(0, i - half_window)
            end = min(len(data), i + half_window + 1)
            smoothed.append(np.mean(data[start:end]))

        return smoothed


def process_video(video_path: str, range_offset: float = 0) -> Dict:
    """Process a single video file"""
    processor = VideoProcessor()
    return processor.process_video(video_path, range_offset)


def extract_runner_data(video_path: str) -> Dict:
    """Extract runner data from video (simplified version for demo)"""
    # This is a simplified version that generates synthetic data
    # In production, you would use the actual video processing

    # Simulate data extraction based on the text file format
    time_points = np.arange(0, 3.5, 0.033)  # 30 fps for 3.5 seconds

    # Generate realistic position data (accelerating runner)
    positions = []
    velocities = []

    # Initial position and velocity
    pos = 0
    vel = 0

    for t in time_points:
        # Acceleration phase (0-2s)
        if t < 2.0:
            acc = 4.5 - t * 0.5  # Decreasing acceleration
            vel += acc * 0.033
        # Constant velocity phase (2-3.5s)
        else:
            vel = vel * 0.98  # Slight deceleration

        # Update position
        pos += vel * 0.033

        # Add some noise
        pos_noise = pos + np.random.normal(0, 0.02)
        vel_noise = vel + np.random.normal(0, 0.1)

        positions.append(pos_noise)
        velocities.append(max(0, vel_noise))

    # Calculate statistics
    valid_velocities = [v for v in velocities if v > 0]

    return {
        'positions': positions,
        'velocities': velocities,
        'timestamps': time_points.tolist(),
        'max_speed': max(valid_velocities) if valid_velocities else 0,
        'avg_speed': np.mean(valid_velocities) if valid_velocities else 0,
        'time': 3.5,
        'distance': 25.0
    }


def merge_range_data(range_data_list: List[Dict]) -> Dict:
    """Merge data from all 4 ranges into complete 100m data"""
    merged = {
        'position_data': {'time': [], 'position': []},
        'velocity_data': {'time': [], 'velocity': []},
        'range_data': range_data_list,
        'max_velocity': 0,
        'avg_velocity': 0,
        'total_distance': 100,
        'total_time': 0
    }

    time_offset = 0
    position_offset = 0

    all_velocities = []

    for i, data in enumerate(range_data_list):
        # Adjust timestamps and positions for each range
        for j, t in enumerate(data['timestamps']):
            merged['position_data']['time'].append(t + time_offset)
            merged['position_data']['position'].append(
                data['positions'][j] + position_offset
            )

            merged['velocity_data']['time'].append(t + time_offset)
            merged['velocity_data']['velocity'].append(data['velocities'][j])

            if data['velocities'][j] > 0:
                all_velocities.append(data['velocities'][j])

        time_offset += data['time']
        position_offset += 25  # Each range is 25m

    # Calculate overall statistics
    if all_velocities:
        merged['max_velocity'] = max(all_velocities)
        merged['avg_velocity'] = np.mean(all_velocities)

    merged['total_time'] = sum(data['time'] for data in range_data_list)

    return merged


def analyze_running_form(video_path: str) -> Dict:
    """Analyze running form and biomechanics"""
    processor = VideoProcessor()
    cap = cv2.VideoCapture(video_path)

    fps = cap.get(cv2.CAP_PROP_FPS)

    # Biomechanical metrics
    stride_lengths = []
    stride_frequencies = []
    body_angles = []

    frame_idx = 0
    prev_foot_contact = None

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = processor.pose.process(frame_rgb)

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark

            # Calculate body angle (trunk lean)
            shoulder = landmarks[processor.mp_pose.PoseLandmark.LEFT_SHOULDER]
            hip = landmarks[processor.mp_pose.PoseLandmark.LEFT_HIP]

            angle = math.degrees(math.atan2(
                shoulder.y - hip.y,
                shoulder.x - hip.x
            ))
            body_angles.append(angle)

            # Detect foot contacts for stride analysis
            left_foot = landmarks[processor.mp_pose.PoseLandmark.LEFT_ANKLE]
            right_foot = landmarks[processor.mp_pose.PoseLandmark.RIGHT_ANKLE]

            # Simple foot contact detection based on vertical position
            if prev_foot_contact is not None:
                # Calculate stride metrics
                pass

            prev_foot_contact = (left_foot.y, right_foot.y)

        frame_idx += 1

    cap.release()

    return {
        'avg_body_angle': np.mean(body_angles) if body_angles else 0,
        'body_angle_std': np.std(body_angles) if body_angles else 0,
        'stride_length_avg': np.mean(stride_lengths) if stride_lengths else 0,
        'stride_frequency_avg': np.mean(stride_frequencies) if stride_frequencies else 0
    }