# RunAnalytics - Running Performance Analysis System

A comprehensive Streamlit application for analyzing running performance using video analysis and deep learning.

## Features

- **Multi-user System**: Support for three user roles:
  - **Admin**: Full access to all features and user management
  - **Coach**: Can view and analyze their runners' performance
  - **Runner**: Can upload videos and view their own performance

- **Video Analysis**: Upload 4 videos capturing different ranges of a 100m track (0-25m, 25-50m, 50-75m, 75-100m)

- **Performance Metrics**:
  - Maximum velocity
  - Average velocity
  - Position tracking
  - Time analysis
  - Range-specific performance

- **Visualization**:
  - Position vs Time charts
  - Velocity vs Time charts
  - Range comparison charts
  - Interactive Plotly visualizations

- **Export Reports**: Generate comprehensive Excel reports with:
  - Summary statistics
  - Detailed data
  - Performance charts
  - Analysis insights

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/runanalytics.git
cd runanalytics
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create the `.streamlit` directory and add the config.toml file:
```bash
mkdir .streamlit
cp config.toml .streamlit/
```

## Running the Application

### Option 1: Using the run script (Linux/Mac)
```bash
chmod +x run.sh
./run.sh
```

### Option 2: Direct command
```bash
streamlit run app.py
```

The application will start on `http://localhost:8501`

## Default Credentials

- **Admin**: 
  - Username: `admin`
  - Password: `admin123`

## Project Structure

```
runanalytics/
│
├── app.py                 # Main Streamlit application
├── auth.py               # Authentication module
├── database.py           # Database operations
├── video_processor.py    # Video processing and analysis
├── report_generator.py   # Report generation functions
├── requirements.txt      # Python dependencies
├── run.sh               # Run script
├── README.md            # This file
├── .streamlit/
│   └── config.toml      # Streamlit configuration
└── runanalytics.db      # SQLite database (created on first run)
```

## Usage

1. **Login/Register**: 
   - Use default admin credentials or register a new account
   - Runners need to specify their coach during registration

2. **Upload Videos**:
   - Navigate to "Video Upload" tab
   - Upload 4 videos, one for each 25m range
   - Click "Process Videos" to analyze

3. **View Analysis**:
   - Go to "Performance Analysis" tab
   - View metrics, charts, and detailed analysis

4. **Generate Reports**:
   - Navigate to "Reports" tab
   - Click "Export to Excel" to download comprehensive report

## Technical Details

### Color Theme
- Primary: `rgb(255, 178, 44)` - Orange
- Secondary: `rgb(133, 72, 54)` - Brown
- Background: `rgb(247, 247, 247)` - Light Gray
- Text: `rgb(0, 0, 0)` - Black

### Font
- Uses 'Prompt' font family throughout the application

### Video Processing
- Uses OpenCV and MediaPipe for pose detection
- Extracts position and velocity data from videos
- Calculates performance metrics

### Database
- SQLite database for user management and performance data
- Tables: users, performance_data, range_performance, video_metadata

## Troubleshooting

1. **MediaPipe Installation Issues**:
   - Ensure you have Python 3.7-3.10
   - Try: `pip install mediapipe --upgrade`

2. **Video Upload Errors**:
   - Check video format (MP4, AVI, MOV supported)
   - Ensure file size is under 200MB

3. **Database Errors**:
   - Delete `runanalytics.db` and restart the app to recreate

## Future Enhancements

- Real-time video processing feedback
- Advanced biomechanical analysis
- Comparison with professional runners
- Mobile app integration
- Cloud storage for videos
- Team management features

## License

This project is licensed under the MIT License.

## Contact

For questions or support, please contact: support@runanalytics.com