# Running Performance Analysis System

A comprehensive Streamlit application for analyzing running performance using video analysis and OpenCV.

## Features

- **Multi-user Authentication**: Support for Admin, Coach, and Runner roles
- **Video Upload**: Upload 4 videos for different running ranges (0-25m, 25-50m, 50-75m, 75-100m)
- **OpenCV Analysis**: Simple human detection using HOG descriptor
- **Performance Visualization**: Interactive charts showing speed and position data
- **Excel Export**: Generate detailed performance reports
- **Database Storage**: SQLite database for persistent data storage

## Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt