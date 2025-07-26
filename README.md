# RunAnalytics - Streamlit Application

A comprehensive running performance analysis application built with Streamlit, featuring video upload, AI-powered performance extraction, and detailed reporting.

## Features

### User Management
- **Three user roles**: Admin, Coach, and Runner
- **Admin**: Full access to all features and user management
- **Coach**: Can view performance data of assigned runners
- **Runner**: Can upload videos and view own performance data

### Video Upload
- Upload 4 video files for different segments of 100m track:
  - Range 1: 0-25 meters
  - Range 2: 25-50 meters
  - Range 3: 50-75 meters
  - Range 4: 75-100 meters

### Performance Analysis
- AI model extracts running performance metrics from videos
- Real-time visualization of:
  - Position vs Time graph
  - Velocity vs Time graph
  - Performance metrics (Max Velocity, Average Velocity, Total Distance, Analysis Time)
  - Speed analysis by segment

### Reports
- Generate comprehensive Excel reports with:
  - Summary statistics
  - Detailed performance data
  - Speed analysis by segment
  - Time-series data for position and velocity

## Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd running-analytics
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
streamlit run app.py
```

## Usage

### First Time Setup
1. The application will create a SQLite database (`running_analytics.db`) on first run
2. Default admin credentials:
   - Username: `admin`
   - Password: `admin123`

### User Creation (Admin only)
1. Login as admin
2. Navigate to "User Management" tab
3. Create coaches and runners
4. Assign runners to coaches

### Video Upload Process
1. Login as runner or admin
2. Go to "Video Upload" tab
3. Upload 4 videos (one for each 25m segment)
4. Click "Process Videos" to analyze

### View Performance
1. Go to "Performance Analysis" tab
2. Select a session from the dropdown
3. View metrics and visualizations

### Generate Reports
1. Go to "Reports" tab
2. Select a session
3. Click "Export to Excel"
4. Download the comprehensive report

## Deep Learning Model Integration

The current implementation uses a mock function (`extract_performance_from_video`) to simulate the deep learning model. To integrate your actual model:

1. Replace the `extract_performance_from_video` function in `app.py`
2. Your model should return a DataFrame with columns:
   - `time`: timestamp in seconds
   - `position`: position in meters
   - `velocity`: velocity in m/s

Example integration:
```python
def extract_performance_from_video(video_file, range_type):
    # Save video temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
        tmp_file.write(video_file.read())
        video_path = tmp_file.name
    
    # Call your deep learning model
    results = your_dl_model.process_video(video_path, range_type)
    
    # Convert results to DataFrame
    df = pd.DataFrame({
        'time': results['timestamps'],
        'position': results['positions'],
        'velocity': results['velocities']
    })
    
    # Clean up
    os.unlink(video_path)
    
    return df
```

## Database Schema

### Users Table
- `id`: Primary key
- `username`: Unique username
- `password`: Hashed password
- `role`: User role (admin/coach/runner)
- `coach_id`: Foreign key to coach (for runners)
- `created_at`: Timestamp

### Sessions Table
- `id`: Primary key
- `runner_id`: Foreign key to user
- `coach_id`: Foreign key to coach
- `session_date`: Timestamp
- `total_distance`: Total distance covered
- `max_velocity`: Maximum velocity achieved
- `avg_velocity`: Average velocity
- `analysis_time`: Total analysis duration

### Performance Data Table
- `id`: Primary key
- `session_id`: Foreign key to session
- `range_type`: Video segment (0-25m, 25-50m, etc.)
- `time_stamp`: Time in seconds
- `position`: Position in meters
- `velocity`: Velocity in m/s

### Video Files Table
- `id`: Primary key
- `session_id`: Foreign key to session
- `range_type`: Video segment
- `file_path`: Path to stored video
- `uploaded_at`: Timestamp

## Customization

### Styling
The application uses custom CSS with:
- **Background**: rgb(247, 247, 247)
- **Primary**: rgb(255, 178, 44)
- **Secondary**: rgb(133, 72, 54)
- **Text**: rgb(0, 0, 0)
- **Font**: Prompt (Google Fonts)

To modify styling, edit the CSS in the `st.markdown()` section at the beginning of `app.py`.

### Performance Metrics
Add new metrics by:
1. Updating the database schema
2. Modifying the `extract_performance_from_video` function
3. Adding visualization components
4. Updating the Excel report generation

## Troubleshooting

### Common Issues
1. **Database errors**: Delete `running_analytics.db` and restart the app
2. **Video processing fails**: Check video format (MP4, AVI, MOV supported)
3. **Login issues**: Ensure correct credentials or reset database

### Debug Mode
Set Streamlit to debug mode:
```bash
streamlit run app.py --server.runOnSave true --logger.level debug
```

## Security Notes
- Passwords are hashed using SHA-256
- Consider implementing additional security measures for production:
  - JWT tokens for authentication
  - HTTPS deployment
  - Environment variables for sensitive data
  - Rate limiting for video uploads

## Future Enhancements
- Real-time video preview during upload
- Batch processing for multiple sessions
- Advanced analytics (acceleration, stride analysis)
- Mobile app integration
- Cloud storage for videos
- Multi-language support