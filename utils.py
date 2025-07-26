import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
import cv2
import tempfile
import os
from datetime import datetime, timedelta


def format_time(seconds: float) -> str:
    """Format seconds to readable time string"""
    if seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.2f}s"


def format_velocity(velocity: float) -> str:
    """Format velocity with appropriate units"""
    return f"{velocity:.3f} m/s"


def calculate_acceleration(velocities: List[float], timestamps: List[float]) -> List[float]:
    """Calculate acceleration from velocity data"""
    accelerations = []

    for i in range(1, len(velocities)):
        dt = timestamps[i] - timestamps[i - 1]
        if dt > 0:
            acc = (velocities[i] - velocities[i - 1]) / dt
            accelerations.append(acc)
        else:
            accelerations.append(0)

    # Add 0 for the first point
    accelerations.insert(0, 0)

    return accelerations


def smooth_data(data: List[float], window_size: int = 5) -> List[float]:
    """Apply moving average smoothing"""
    if len(data) < window_size:
        return data

    smoothed = []
    half_window = window_size // 2

    for i in range(len(data)):
        start = max(0, i - half_window)
        end = min(len(data), i + half_window + 1)
        smoothed.append(np.mean(data[start:end]))

    return smoothed


def detect_outliers(data: List[float], threshold: float = 3.0) -> List[int]:
    """Detect outliers using z-score method"""
    if len(data) < 3:
        return []

    mean = np.mean(data)
    std = np.std(data)

    outliers = []
    for i, value in enumerate(data):
        z_score = abs((value - mean) / std) if std > 0 else 0
        if z_score > threshold:
            outliers.append(i)

    return outliers


def interpolate_missing_data(data: List[float], indices: List[int]) -> List[float]:
    """Interpolate missing or invalid data points"""
    data_copy = data.copy()

    for idx in indices:
        if 0 < idx < len(data) - 1:
            # Linear interpolation
            data_copy[idx] = (data[idx - 1] + data[idx + 1]) / 2
        elif idx == 0 and len(data) > 1:
            data_copy[idx] = data[1]
        elif idx == len(data) - 1 and len(data) > 1:
            data_copy[idx] = data[-2]

    return data_copy


def extract_video_metadata(video_path: str) -> Dict:
    """Extract metadata from video file"""
    cap = cv2.VideoCapture(video_path)

    metadata = {
        'fps': cap.get(cv2.CAP_PROP_FPS),
        'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        'duration': 0,
        'codec': int(cap.get(cv2.CAP_PROP_FOURCC)),
        'file_size': os.path.getsize(video_path) if os.path.exists(video_path) else 0
    }

    if metadata['fps'] > 0:
        metadata['duration'] = metadata['frame_count'] / metadata['fps']

    # Convert codec to string
    codec_chars = [chr((metadata['codec'] >> 8 * i) & 0xFF) for i in range(4)]
    metadata['codec_str'] = ''.join(codec_chars)

    cap.release()

    return metadata


def validate_video_file(video_path: str) -> Tuple[bool, str]:
    """Validate video file for processing"""
    if not os.path.exists(video_path):
        return False, "Video file not found"

    try:
        metadata = extract_video_metadata(video_path)

        if metadata['frame_count'] == 0:
            return False, "Video has no frames"

        if metadata['fps'] == 0:
            return False, "Invalid frame rate"

        if metadata['width'] == 0 or metadata['height'] == 0:
            return False, "Invalid video dimensions"

        # Check duration (should be reasonable for 25m sprint)
        if metadata['duration'] < 1.0 or metadata['duration'] > 10.0:
            return False, f"Video duration ({metadata['duration']:.1f}s) seems incorrect for 25m range"

        return True, "Video is valid"

    except Exception as e:
        return False, f"Error validating video: {str(e)}"


def calculate_stride_metrics(positions: List[float], timestamps: List[float],
                             threshold: float = 0.5) -> Dict:
    """Calculate stride length and frequency from position data"""
    # Detect peaks in velocity to identify strides
    velocities = []
    for i in range(1, len(positions)):
        dt = timestamps[i] - timestamps[i - 1]
        if dt > 0:
            v = (positions[i] - positions[i - 1]) / dt
            velocities.append(v)
        else:
            velocities.append(0)

    # Smooth velocities
    velocities = smooth_data(velocities, window_size=3)

    # Find local maxima (peaks)
    peaks = []
    for i in range(1, len(velocities) - 1):
        if velocities[i] > velocities[i - 1] and velocities[i] > velocities[i + 1]:
            if velocities[i] > threshold:  # Only significant peaks
                peaks.append(i)

    # Calculate stride metrics
    stride_lengths = []
    stride_times = []

    for i in range(1, len(peaks)):
        # Stride length
        length = positions[peaks[i]] - positions[peaks[i - 1]]
        stride_lengths.append(length)

        # Stride time
        time = timestamps[peaks[i]] - timestamps[peaks[i - 1]]
        stride_times.append(time)

    metrics = {
        'num_strides': len(stride_lengths),
        'avg_stride_length': np.mean(stride_lengths) if stride_lengths else 0,
        'std_stride_length': np.std(stride_lengths) if stride_lengths else 0,
        'avg_stride_frequency': 1 / np.mean(stride_times) if stride_times else 0,
        'stride_consistency': 1 - (np.std(stride_lengths) / np.mean(stride_lengths)) if stride_lengths else 0
    }

    return metrics


def generate_performance_summary(performance_data: Dict) -> str:
    """Generate a text summary of performance"""
    summary = []

    # Overall performance
    summary.append(f"Maximum Velocity: {performance_data['max_velocity']:.3f} m/s")
    summary.append(f"Average Velocity: {performance_data['avg_velocity']:.3f} m/s")
    summary.append(f"Total Time: {performance_data['total_time']:.3f} seconds")
    summary.append(f"Total Distance: {performance_data['total_distance']:.1f} meters")

    # Speed comparison to world records
    world_record_speed = 12.27  # Usain Bolt's max speed
    speed_percentage = (performance_data['max_velocity'] / world_record_speed) * 100
    summary.append(f"\nSpeed compared to world record: {speed_percentage:.1f}%")

    # Range analysis
    summary.append("\nRange Performance:")
    ranges = ["0-25m", "25-50m", "50-75m", "75-100m"]
    for i, (range_name, range_data) in enumerate(zip(ranges, performance_data.get('range_data', []))):
        summary.append(f"  {range_name}: {range_data.get('avg_speed', 0):.3f} m/s avg, "
                       f"{range_data.get('time', 0):.3f}s")

    # Performance insights
    if performance_data.get('range_data'):
        # Find best range
        speeds = [r.get('avg_speed', 0) for r in performance_data['range_data']]
        best_range_idx = speeds.index(max(speeds))
        summary.append(f"\nBest performance in: {ranges[best_range_idx]}")

        # Check acceleration pattern
        if speeds[0] < speeds[1]:
            summary.append("Good acceleration pattern observed")
        else:
            summary.append("Consider working on initial acceleration")

    return "\n".join(summary)


def create_training_recommendations(performance_data: Dict) -> List[Dict]:
    """Generate training recommendations based on performance"""
    recommendations = []

    # Analyze velocity patterns
    max_vel = performance_data.get('max_velocity', 0)
    avg_vel = performance_data.get('avg_velocity', 0)

    # Speed endurance
    if max_vel > 0:
        speed_endurance = (avg_vel / max_vel) * 100
        if speed_endurance < 80:
            recommendations.append({
                'category': 'Speed Endurance',
                'issue': 'Significant speed drop-off detected',
                'recommendation': 'Focus on speed endurance training with repeated 60-80m sprints'
            })

    # Acceleration
    range_data = performance_data.get('range_data', [])
    if len(range_data) >= 2:
        early_speed = range_data[0].get('avg_speed', 0)
        mid_speed = range_data[1].get('avg_speed', 0)

        if early_speed < mid_speed * 0.8:
            recommendations.append({
                'category': 'Acceleration',
                'issue': 'Slow initial acceleration',
                'recommendation': 'Include explosive starts and plyometric exercises'
            })

    # Max velocity
    if max_vel < 8.0:  # Below average for trained runners
        recommendations.append({
            'category': 'Maximum Velocity',
            'issue': 'Low maximum velocity',
            'recommendation': 'Work on technique and strength training'
        })

    # Deceleration
    if len(range_data) >= 4:
        final_speed = range_data[3].get('avg_speed', 0)
        peak_speed = max([r.get('avg_speed', 0) for r in range_data])

        if final_speed < peak_speed * 0.85:
            recommendations.append({
                'category': 'Speed Maintenance',
                'issue': 'Significant deceleration in final phase',
                'recommendation': 'Improve lactate threshold with tempo runs'
            })

    return recommendations


def compare_performances(current: Dict, previous: Dict) -> Dict:
    """Compare two performance datasets"""
    comparison = {
        'max_velocity_change': current['max_velocity'] - previous['max_velocity'],
        'avg_velocity_change': current['avg_velocity'] - previous['avg_velocity'],
        'time_change': current['total_time'] - previous['total_time'],
        'improvements': [],
        'regressions': []
    }

    # Check improvements
    if comparison['max_velocity_change'] > 0.1:
        comparison['improvements'].append(f"Max velocity improved by {comparison['max_velocity_change']:.3f} m/s")

    if comparison['time_change'] < -0.1:
        comparison['improvements'].append(f"Time improved by {abs(comparison['time_change']):.3f} seconds")

    # Check regressions
    if comparison['max_velocity_change'] < -0.1:
        comparison['regressions'].append(f"Max velocity decreased by {abs(comparison['max_velocity_change']):.3f} m/s")

    if comparison['time_change'] > 0.1:
        comparison['regressions'].append(f"Time increased by {comparison['time_change']:.3f} seconds")

    # Calculate overall improvement
    max_vel_improvement = (comparison['max_velocity_change'] / previous['max_velocity']) * 100 if previous[
                                                                                                      'max_velocity'] > 0 else 0
    time_improvement = -(comparison['time_change'] / previous['total_time']) * 100 if previous['total_time'] > 0 else 0

    comparison['overall_improvement'] = (max_vel_improvement + time_improvement) / 2

    return comparison