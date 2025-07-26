import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import hashlib
import sqlite3
import os
from io import BytesIO
import xlsxwriter
import tempfile
import time

# Page configuration
st.set_page_config(
    page_title="RunAnalytics",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap');

    * {
        font-family: 'Prompt', sans-serif !important;
    }

    .stApp {
        background-color: rgb(247, 247, 247);
    }

    .main-header {
        background-color: rgb(133, 72, 54);
        color: white;
        padding: 1rem 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .user-info {
        background-color: rgb(255, 178, 44);
        color: rgb(0, 0, 0);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 500;
    }

    .metric-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 1rem;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: rgb(133, 72, 54);
    }

    .metric-label {
        font-size: 0.9rem;
        color: rgb(100, 100, 100);
        margin-top: 0.5rem;
    }

    .upload-box {
        border: 2px dashed rgb(255, 178, 44);
        background-color: rgba(255, 178, 44, 0.1);
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 1rem;
    }

    .stButton > button {
        background-color: rgb(255, 178, 44);
        color: rgb(0, 0, 0);
        font-weight: 500;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 25px;
        transition: all 0.3s;
    }

    .stButton > button:hover {
        background-color: rgb(133, 72, 54);
        color: white;
    }

    .success-message {
        background-color: #4CAF50;
        color: white;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }

    .tab-content {
        background-color: white;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }

    .video-status {
        text-align: center;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }

    .video-uploaded {
        background-color: rgba(76, 175, 80, 0.1);
        color: #4CAF50;
        border: 1px solid #4CAF50;
    }

    .video-pending {
        background-color: rgba(255, 178, 44, 0.1);
        color: rgb(133, 72, 54);
        border: 1px dashed rgb(255, 178, 44);
    }
</style>
""", unsafe_allow_html=True)


# Database setup
def init_db():
    """Initialize database with required tables"""
    conn = sqlite3.connect('running_analytics.db')
    c = conn.cursor()

    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     username
                     TEXT
                     UNIQUE
                     NOT
                     NULL,
                     password
                     TEXT
                     NOT
                     NULL,
                     role
                     TEXT
                     NOT
                     NULL,
                     coach_id
                     INTEGER,
                     created_at
                     TIMESTAMP
                     DEFAULT
                     CURRENT_TIMESTAMP
                 )''')

    # Running sessions table
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
    (
        id
        INTEGER
        PRIMARY
        KEY
        AUTOINCREMENT,
        runner_id
        INTEGER
        NOT
        NULL,
        coach_id
        INTEGER,
        session_date
        TIMESTAMP
        DEFAULT
        CURRENT_TIMESTAMP,
        total_distance
        REAL,
        max_velocity
        REAL,
        avg_velocity
        REAL,
        analysis_time
        REAL,
        FOREIGN
        KEY
                 (
        runner_id
                 ) REFERENCES users
                 (
                     id
                 ),
        FOREIGN KEY
                 (
                     coach_id
                 ) REFERENCES users
                 (
                     id
                 ))''')

    # Performance data table
    c.execute('''CREATE TABLE IF NOT EXISTS performance_data
    (
        id
        INTEGER
        PRIMARY
        KEY
        AUTOINCREMENT,
        session_id
        INTEGER
        NOT
        NULL,
        range_type
        TEXT
        NOT
        NULL,
        time_stamp
        REAL,
        position
        REAL,
        velocity
        REAL,
        FOREIGN
        KEY
                 (
        session_id
                 ) REFERENCES sessions
                 (
                     id
                 ))''')

    # Video files table
    c.execute('''CREATE TABLE IF NOT EXISTS video_files
    (
        id
        INTEGER
        PRIMARY
        KEY
        AUTOINCREMENT,
        session_id
        INTEGER
        NOT
        NULL,
        range_type
        TEXT
        NOT
        NULL,
        file_path
        TEXT,
        uploaded_at
        TIMESTAMP
        DEFAULT
        CURRENT_TIMESTAMP,
        FOREIGN
        KEY
                 (
        session_id
                 ) REFERENCES sessions
                 (
                     id
                 ))''')

    # Insert default admin user if not exists
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ("admin", admin_pass, "admin"))

    # Insert sample coach and runner for demo
    c.execute("SELECT * FROM users WHERE username = 'coach1'")
    if not c.fetchone():
        coach_pass = hashlib.sha256("coach123".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ("coach1", coach_pass, "coach"))

        # Get coach id
        c.execute("SELECT id FROM users WHERE username = 'coach1'")
        coach_id = c.fetchone()[0]

        # Insert sample runner
        runner_pass = hashlib.sha256("runner123".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role, coach_id) VALUES (?, ?, ?, ?)",
                  ("runner1", runner_pass, "runner", coach_id))

    conn.commit()
    conn.close()


# Authentication functions
def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate_user(username, password):
    """Authenticate user and return user details"""
    conn = sqlite3.connect('running_analytics.db')
    c = conn.cursor()
    c.execute("SELECT id, role, coach_id FROM users WHERE username = ? AND password = ?",
              (username, hash_password(password)))
    result = c.fetchone()
    conn.close()
    return result


def create_user(username, password, role, coach_id=None):
    """Create new user"""
    conn = sqlite3.connect('running_analytics.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, role, coach_id) VALUES (?, ?, ?, ?)",
                  (username, hash_password(password), role, coach_id))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

    # Deep learning model simulation
    def extract_performance_from_video(video_file, range_type):
        """
        Simulate deep learning model extraction
        In production, replace this with your actual deep learning model
        """
        # Simulate processing time
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i in range(100):
            progress_bar.progress(i + 1)
            status_text.text(f'Processing {range_type}: {i + 1}%')
            time.sleep(0.02)

        progress_bar.empty()
        status_text.empty()

        # Generate realistic mock data based on the sample files
        if range_type == "0-25m":
            # Start phase - acceleration
            t = np.arange(0, 3.5, 0.033)
            # Position: starts at ~0.8m, accelerates
            x = 0.863 + (t * 2.5) + (0.5 * 2.8 * t ** 2)
            # Velocity: starts low, increases
            v = 0.089 + (2.8 * t) + np.random.normal(0, 0.1, len(t))
            v = np.maximum(v, 0.05)  # Ensure positive velocity

        elif range_type == "25-50m":
            # Peak acceleration phase
            t = np.arange(3.5, 7.0, 0.033)
            t_rel = t - 3.5
            # Continue from 25m mark
            x = 25 + (t_rel * 8.5) + (0.3 * t_rel ** 2)
            # High velocity with slight increase
            v = 8.5 + (0.5 * t_rel) + np.random.normal(0, 0.2, len(t))

        elif range_type == "50-75m":
            # Maintaining phase
            t = np.arange(7.0, 10.5, 0.033)
            t_rel = t - 7.0
            # Continue from 50m mark
            x = 50 + (t_rel * 8.7)
            # Stable high velocity
            v = 8.7 + np.random.normal(0, 0.15, len(t))

        else:  # 75-100m
            # Slight deceleration phase
            t = np.arange(10.5, 14.0, 0.033)
            t_rel = t - 10.5
            # Continue from 75m mark
            x = 75 + (t_rel * 8.2) - (0.05 * t_rel ** 2)
            # Gradual velocity decrease
            v = 8.2 - (0.15 * t_rel) + np.random.normal(0, 0.1, len(t))

        return pd.DataFrame({
            'time': t,
            'position': x,
            'velocity': np.abs(v)  # Ensure positive velocities
        })

    # Visualization functions
    def create_position_time_chart(df):
        """Create position vs time chart"""
        fig = go.Figure()

        # Add trace for each range type with different colors
        colors = {
            '0-25m': 'rgb(133, 72, 54)',
            '25-50m': 'rgb(255, 178, 44)',
            '50-75m': 'rgb(76, 175, 80)',
            '75-100m': 'rgb(33, 150, 243)'
        }

        for range_type in df['range_type'].unique():
            range_data = df[df['range_type'] == range_type]
            fig.add_trace(go.Scatter(
                x=range_data['time_stamp'],
                y=range_data['position'],
                mode='lines+markers',
                name=range_type,
                line=dict(color=colors.get(range_type, 'black'), width=2),
                marker=dict(size=4)
            ))

        fig.update_layout(
            title='Position vs Time',
            xaxis_title='Time (s)',
            yaxis_title='Position (m)',
            plot_bgcolor='white',
            paper_bgcolor='rgb(247, 247, 247)',
            font=dict(family="Prompt"),
            hovermode='x unified'
        )

        return fig

    def create_velocity_time_chart(df):
        """Create velocity vs time chart"""
        fig = go.Figure()

        # Calculate average velocity for each time interval
        time_intervals = np.arange(0, df['time_stamp'].max(), 0.5)
        avg_velocities = []

        for i in range(len(time_intervals) - 1):
            mask = (df['time_stamp'] >= time_intervals[i]) & (df['time_stamp'] < time_intervals[i + 1])
            avg_v = df[mask]['velocity'].mean() if mask.any() else 0
            avg_velocities.append(avg_v)

        fig.add_trace(go.Bar(
            x=time_intervals[:-1] + 0.25,  # Center bars
            y=avg_velocities,
            name='Velocity',
            marker_color='rgb(255, 178, 44)',
            width=0.4
        ))

        fig.update_layout(
            title='Velocity vs Time',
            xaxis_title='Time (s)',
            yaxis_title='Velocity (m/s)',
            plot_bgcolor='white',
            paper_bgcolor='rgb(247, 247, 247)',
            font=dict(family="Prompt"),
            showlegend=False
        )

        return fig

    def create_speed_heatmap(df):
        """Create speed heatmap by position"""
        # Create bins for position
        position_bins = np.arange(0, 105, 5)
        df['position_bin'] = pd.cut(df['position'], bins=position_bins, labels=position_bins[:-1])

        # Calculate average speed for each bin
        heatmap_data = df.groupby('position_bin')['velocity'].mean().reset_index()

        fig = go.Figure(data=go.Heatmap(
            x=heatmap_data['position_bin'],
            y=['Speed'],
            z=[heatmap_data['velocity'].values],
            colorscale='YlOrRd',
            showscale=True,
            colorbar=dict(title="Velocity (m/s)")
        ))

        fig.update_layout(
            title='Speed Heatmap by Position',
            xaxis_title='Position (m)',
            yaxis_title='',
            plot_bgcolor='white',
            paper_bgcolor='rgb(247, 247, 247)',
            font=dict(family="Prompt"),
            height=200
        )

        return fig

    def generate_excel_report(session_data, performance_data):
        """Generate comprehensive Excel report"""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#855448',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Arial',
            'font_size': 12
        })

        subheader_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFB22C',
            'font_color': 'black',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Arial',
            'font_size': 11
        })

        data_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Arial',
            'font_size': 10
        })

        number_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Arial',
            'font_size': 10,
            'num_format': '0.000'
        })

        # Sheet 1: Summary
        summary_sheet = workbook.add_worksheet('Summary')
        summary_sheet.set_column('A:B', 20)

        # Title
        summary_sheet.merge_range('A1:B1', 'Running Performance Analysis Report', header_format)
        summary_sheet.merge_range('A2:B2', f'Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', data_format)

        # Session details
        row = 4
        summary_data = [
            ['Runner', session_data.get('username', 'N/A')],
            ['Session Date', session_data['session_date']],
            ['Total Distance', f"{session_data['total_distance']:.1f} m"],
            ['Max Velocity', f"{session_data['max_velocity']:.3f} m/s"],
            ['Average Velocity', f"{session_data['avg_velocity']:.3f} m/s"],
            ['Analysis Time', f"{session_data['analysis_time']:.3f} s"]
        ]

        for item in summary_data:
            summary_sheet.write(row, 0, item[0], subheader_format)
            summary_sheet.write(row, 1, item[1], data_format)
            row += 1

        # Sheet 2: Speed Analysis
        speed_sheet = workbook.add_worksheet('Speed')
        speed_sheet.set_column('A:E', 15)

        speed_sheet.merge_range('A1:E1', '100-Meter Speed Analysis', header_format)

        # Headers
        speed_headers = ['Distance (m)', 'Avg Speed (m/s)', 'Max Speed (m/s)', 'Min Speed (m/s)', 'Time (s)']
        for col, header in enumerate(speed_headers):
            speed_sheet.write(2, col, header, subheader_format)

        # Calculate segment data
        segments = ['0-25', '25-50', '50-75', '75-100']
        row = 3

        for segment in segments:
            range_type = f"{segment}m"
            segment_data = performance_data[performance_data['range_type'] == range_type]

            if not segment_data.empty:
                avg_speed = segment_data['velocity'].mean()
                max_speed = segment_data['velocity'].max()
                min_speed = segment_data['velocity'].min()
                time_taken = segment_data['time_stamp'].max() - segment_data['time_stamp'].min()

                speed_sheet.write(row, 0, segment, data_format)
                speed_sheet.write(row, 1, avg_speed, number_format)
                speed_sheet.write(row, 2, max_speed, number_format)
                speed_sheet.write(row, 3, min_speed, number_format)
                speed_sheet.write(row, 4, time_taken, number_format)
                row += 1

        # Sheet 3: Detailed Data
        for range_type in ['0-25m', '25-50m', '50-75m', '75-100m']:
            sheet_name = range_type.replace('-', '_')
            detail_sheet = workbook.add_worksheet(sheet_name)
            detail_sheet.set_column('A:C', 15)

            # Title
            detail_sheet.merge_range('A1:C1', f'Performance Data - {range_type}', header_format)

            # Headers
            detail_sheet.write('A3', 'Time (s)', subheader_format)
            detail_sheet.write('B3', 'Position (m)', subheader_format)
            detail_sheet.write('C3', 'Velocity (m/s)', subheader_format)

            # Data
            range_data = performance_data[performance_data['range_type'] == range_type].sort_values('time_stamp')
            row = 4

            for _, data_row in range_data.iterrows():
                detail_sheet.write(row, 0, data_row['time_stamp'], number_format)
                detail_sheet.write(row, 1, data_row['position'], number_format)
                detail_sheet.write(row, 2, data_row['velocity'], number_format)
                row += 1

            # Add chart
            if len(range_data) > 1:
                chart = workbook.add_chart({'type': 'line'})
                chart.add_series({
                    'name': 'Velocity',
                    'categories': [sheet_name, 4, 0, row - 1, 0],
                    'values': [sheet_name, 4, 2, row - 1, 2],
                    'line': {'color': '#FFB22C', 'width': 2}
                })
                chart.set_title({'name': f'Velocity Profile - {range_type}'})
                chart.set_x_axis({'name': 'Time (s)'})
                chart.set_y_axis({'name': 'Velocity (m/s)'})
                chart.set_style(10)
                detail_sheet.insert_chart('E3', chart, {'x_scale': 1.5, 'y_scale': 1.5})

        workbook.close()
        output.seek(0)
        return output

    # Main application
    def main():
        # Initialize database
        init_db()

        # Session state initialization
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user_id' not in st.session_state:
            st.session_state.user_id = None
        if 'user_role' not in st.session_state:
            st.session_state.user_role = None
        if 'username' not in st.session_state:
            st.session_state.username = None
        if 'uploaded_videos' not in st.session_state:
            st.session_state.uploaded_videos = {}

        # Login page
        if not st.session_state.authenticated:
            st.markdown('<div class="main-header"><h1>🏃 RunAnalytics</h1><span class="user-info">RUNNER</span></div>',
                        unsafe_allow_html=True)

            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown("### Welcome to RunAnalytics")
                st.markdown("Track your running progress and performance metrics")

                with st.form("login_form"):
                    username = st.text_input("Username", placeholder="Enter your username")
                    password = st.text_input("Password", type="password", placeholder="Enter your password")
                    submit = st.form_submit_button("Login", use_container_width=True)

                    if submit:
                        if username and password:
                            result = authenticate_user(username, password)
                            if result:
                                st.session_state.authenticated = True
                                st.session_state.user_id = result[0]
                                st.session_state.user_role = result[1]
                                st.session_state.username = username
                                st.rerun()
                            else:
                                st.error("❌ Invalid username or password")
                        else:
                            st.warning("⚠️ Please enter both username and password")

                st.markdown("---")

                # Demo credentials
                st.info("""
                **Demo Credentials:**
                - Admin: `admin` / `admin123`
                - Coach: `coach1` / `coach123`
                - Runner: `runner1` / `runner123`
                """)

        else:
            # Main application header
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f'<div class="main-header"><h1>🏃 RunAnalytics</h1></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(
                    f'<div class="user-info">👤 {st.session_state.username} ({st.session_state.user_role.upper()})</div>',
                    unsafe_allow_html=True)
                if st.button("Logout", use_container_width=True):
                    for key in st.session_state.keys():
                        del st.session_state[key]
                    st.rerun()

            st.markdown("Track your running progress and performance metrics")

            # Role-based navigation
            if st.session_state.user_role == "admin":
                tabs = st.tabs(["📹 Video Upload", "📊 Performance Analysis", "📑 Reports", "👥 User Management"])
                tab_video, tab_analysis, tab_reports, tab_users = tabs
            else:
                tabs = st.tabs(["📹 Video Upload", "📊 Performance Analysis", "📑 Reports"])
                tab_video, tab_analysis, tab_reports = tabs
                tab_users = None

            # Tab 1: Video Upload
            with tab_video:
                st.markdown("## 📹 Video Upload for Analysis")
                st.markdown("Upload videos for each range of the 100-meter track. Each camera captures 25 meters.")

                # Check if videos are already uploaded
                st.markdown("### Upload Status")
                col1, col2 = st.columns(2)
                ranges = ["0-25m", "25-50m", "50-75m", "75-100m"]

                for i, range_type in enumerate(ranges):
                    with col1 if i < 2 else col2:
                        if range_type in st.session_state.uploaded_videos:
                            st.markdown(f'''
                                <div class="video-status video-uploaded">
                                    ✅ Range {i + 1}: {range_type} - Video Uploaded
                                </div>
                                ''', unsafe_allow_html=True)
                        else:
                            st.markdown(f'''
                                <div class="video-status video-pending">
                                    📹 Range {i + 1}: {range_type} - Pending Upload
                                </div>
                                ''', unsafe_allow_html=True)

                st.markdown("---")

                # Video upload section
                st.markdown("### Upload Videos")
                col1, col2 = st.columns(2)

                for i, range_type in enumerate(ranges):
                    with col1 if i < 2 else col2:
                        with st.expander(f"📹 Range {i + 1}: {range_type}", expanded=True):
                            uploaded_file = st.file_uploader(
                                f"Select video file",
                                type=['mp4', 'avi', 'mov'],
                                key=f"video_{range_type}",
                                help=f"Upload video for {range_type} segment"
                            )

                            if uploaded_file is not None:
                                st.session_state.uploaded_videos[range_type] = uploaded_file
                                st.success(f"✅ Video uploaded successfully!")
                                st.rerun()

                # Process videos button
                st.markdown("---")
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    uploaded_count = len(st.session_state.uploaded_videos)
                    if uploaded_count == 4:
                        if st.button("🎯 Process All Videos", use_container_width=True, type="primary"):
                            with st.spinner("Processing videos with AI model..."):
                                # Create new session
                                conn = sqlite3.connect('running_analytics.db')
                                c = conn.cursor()

                                # Get coach_id for runner
                                coach_id = None
                                if st.session_state.user_role == "runner":
                                    c.execute("SELECT coach_id FROM users WHERE id = ?", (st.session_state.user_id,))
                                    result = c.fetchone()
                                    coach_id = result[0] if result else None

                                # Insert session
                                c.execute("""INSERT INTO sessions (runner_id, coach_id, total_distance, max_velocity,
                                                                   avg_velocity, analysis_time)
                                             VALUES (?, ?, ?, ?, ?, ?)""",
                                          (st.session_state.user_id, coach_id, 100.0, 0.0, 0.0, 0.0))
                                session_id = c.lastrowid

                                all_velocities = []
                                all_times = []

                                # Process each video
                                st.markdown("### Processing Progress")
                                for range_type, video_file in st.session_state.uploaded_videos.items():
                                    st.markdown(f"**Processing {range_type}...**")

                                    # Extract performance data
                                    performance_df = extract_performance_from_video(video_file, range_type)

                                    # Store performance data
                                    for _, row in performance_df.iterrows():
                                        c.execute(
                                            """INSERT INTO performance_data (session_id, range_type, time_stamp, position, velocity)
                                               VALUES (?, ?, ?, ?, ?)""",
                                                  (session_id, range_type, row['time'], row['position'], row['velocity']))
                                        all_velocities.append(row['velocity'])
                                        all_times.append(row['time'])

                                    st.success(f"✅ {range_type} processed successfully!")

                                # Update session with calculated metrics
                                max_velocity = max(all_velocities) if all_velocities else 0
                                avg_velocity = np.mean(all_velocities) if all_velocities else 0
                                analysis_time = max(all_times) - min(all_times) if all_times else 0

                                c.execute("""UPDATE sessions SET max_velocity = ?, avg_velocity = ?, analysis_time = ?
                                             WHERE id = ?""",
                                          (max_velocity, avg_velocity, analysis_time, session_id))

                                conn.commit()
                                conn.close()

                                st.balloons()
                                st.success("🎉 All videos processed successfully! Check the Performance Analysis tab.")
                                st.session_state.uploaded_videos = {}
                                time.sleep(2)
                                st.rerun()
                    else:
                        st.warning(f"⚠️ Please upload all 4 videos before processing. Currently uploaded: {uploaded_count}/4")

                        # Clear uploads button
                        if uploaded_count > 0:
                            if st.button("🗑️ Clear All Uploads", use_container_width=True):
                                st.session_state.uploaded_videos = {}
                                st.rerun()

                    # Tab 2: Performance Analysis
                    with tab_analysis:
                        st.markdown("## 📊 Performance Analysis")

                        # Get sessions based on user role
                        conn = sqlite3.connect('running_analytics.db')

                        if st.session_state.user_role == "admin":
                            sessions_df = pd.read_sql_query("""
                                                            SELECT s.*, u.username
                                                            FROM sessions s
                                                                     JOIN users u ON s.runner_id = u.id
                                                            ORDER BY s.session_date DESC
                                                            """, conn)
                        elif st.session_state.user_role == "coach":
                            sessions_df = pd.read_sql_query("""
                                                            SELECT s.*, u.username
                                                            FROM sessions s
                                                                     JOIN users u ON s.runner_id = u.id
                                                            WHERE s.coach_id = ?
                                                            ORDER BY s.session_date DESC
                                                            """, conn, params=(st.session_state.user_id,))
                        else:  # runner
                            sessions_df = pd.read_sql_query("""
                                                            SELECT s.*, u.username
                                                            FROM sessions s
                                                                     JOIN users u ON s.runner_id = u.id
                                                            WHERE s.runner_id = ?
                                                            ORDER BY s.session_date DESC
                                                            """, conn, params=(st.session_state.user_id,))

                        if not sessions_df.empty:
                            # Session selector
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                selected_session = st.selectbox(
                                    "Select Session",
                                    sessions_df['id'].tolist(),
                                    format_func=lambda
                                        x: f"Session {x} - {sessions_df[sessions_df['id'] == x]['username'].iloc[0]} - {pd.to_datetime(sessions_df[sessions_df['id'] == x]['session_date'].iloc[0]).strftime('%Y-%m-%d %H:%M')}"
                                )

                            session_data = sessions_df[sessions_df['id'] == selected_session].iloc[0]

                            # Display metrics
                            st.markdown("### Performance Metrics")
                            col1, col2, col3, col4 = st.columns(4)

                            with col1:
                                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                                st.markdown(f'<div class="metric-label">Max Velocity</div>', unsafe_allow_html=True)
                                st.markdown(f'<div class="metric-value">{session_data["max_velocity"]:.3f} m/s</div>',
                                            unsafe_allow_html=True)
                                st.markdown('<div class="metric-label">Peak speed achieved</div>',
                                            unsafe_allow_html=True)
                                st.markdown('</div>', unsafe_allow_html=True)

                            with col2:
                                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                                st.markdown(f'<div class="metric-label">Avg Velocity</div>', unsafe_allow_html=True)
                                st.markdown(f'<div class="metric-value">{session_data["avg_velocity"]:.3f} m/s</div>',
                                            unsafe_allow_html=True)
                                st.markdown('<div class="metric-label">Average speed</div>', unsafe_allow_html=True)
                                st.markdown('</div>', unsafe_allow_html=True)

                            with col3:
                                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                                st.markdown(f'<div class="metric-label">Total Distance</div>', unsafe_allow_html=True)
                                st.markdown(f'<div class="metric-value">{session_data["total_distance"]:.1f} m</div>',
                                            unsafe_allow_html=True)
                                st.markdown('<div class="metric-label">Distance covered</div>', unsafe_allow_html=True)
                                st.markdown('</div>', unsafe_allow_html=True)

                            with col4:
                                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                                st.markdown(f'<div class="metric-label">Analysis Time</div>', unsafe_allow_html=True)
                                st.markdown(f'<div class="metric-value">{session_data["analysis_time"]:.3f} s</div>',
                                            unsafe_allow_html=True)
                                st.markdown('<div class="metric-label">Total analysis duration</div>',
                                            unsafe_allow_html=True)
                                st.markdown('</div>', unsafe_allow_html=True)

                            # Get performance data
                            performance_df = pd.read_sql_query("""
                                                               SELECT *
                                                               FROM performance_data
                                                               WHERE session_id = ?
                                                               ORDER BY time_stamp
                                                               """, conn, params=(selected_session,))

                            if not performance_df.empty:
                                # Visualizations
                                st.markdown("### Performance Visualizations")

                                # Position vs Time and Velocity vs Time charts
                                col1, col2 = st.columns(2)

                                with col1:
                                    fig_position = create_position_time_chart(performance_df)
                                    st.plotly_chart(fig_position, use_container_width=True)

                                with col2:
                                    fig_velocity = create_velocity_time_chart(performance_df)
                                    st.plotly_chart(fig_velocity, use_container_width=True)

                                # Speed heatmap
                                fig_heatmap = create_speed_heatmap(performance_df)
                                st.plotly_chart(fig_heatmap, use_container_width=True)

                                # Speed by segment table
                                st.markdown("### Speed Analysis by Segment")
                                segment_data = []

                                for range_type in ['0-25m', '25-50m', '50-75m', '75-100m']:
                                    range_df = performance_df[performance_df['range_type'] == range_type]
                                    if not range_df.empty:
                                        segment_data.append({
                                            'Segment': range_type,
                                            'Average Speed (m/s)': f"{range_df['velocity'].mean():.3f}",
                                            'Max Speed (m/s)': f"{range_df['velocity'].max():.3f}",
                                            'Min Speed (m/s)': f"{range_df['velocity'].min():.3f}",
                                            'Time (s)': f"{range_df['time_stamp'].max() - range_df['time_stamp'].min():.3f}"
                                        })

                                if segment_data:
                                    segment_df = pd.DataFrame(segment_data)
                                    st.dataframe(segment_df, use_container_width=True, hide_index=True)
                            else:
                                st.warning("No performance data found for this session.")
                        else:
                            st.info("📊 No performance data available. Please upload and process videos first.")

                        conn.close()

                    # Tab 3: Reports
                    with tab_reports:
                        st.markdown("## 📑 Performance Reports")
                        st.markdown("Generate and download detailed performance analysis reports.")

                        # Get sessions for report generation
                        conn = sqlite3.connect('running_analytics.db')

                        if st.session_state.user_role == "admin":
                            sessions_df = pd.read_sql_query("""
                                                            SELECT s.*, u.username
                                                            FROM sessions s
                                                                     JOIN users u ON s.runner_id = u.id
                                                            ORDER BY s.session_date DESC
                                                            """, conn)
                        elif st.session_state.user_role == "coach":
                            sessions_df = pd.read_sql_query("""
                                                            SELECT s.*, u.username
                                                            FROM sessions s
                                                                     JOIN users u ON s.runner_id = u.id
                                                            WHERE s.coach_id = ?
                                                            ORDER BY s.session_date DESC
                                                            """, conn, params=(st.session_state.user_id,))
                        else:  # runner
                            sessions_df = pd.read_sql_query("""
                                                            SELECT s.*, u.username
                                                            FROM sessions s
                                                                     JOIN users u ON s.runner_id = u.id
                                                            WHERE s.runner_id = ?
                                                            ORDER BY s.session_date DESC
                                                            """, conn, params=(st.session_state.user_id,))

                        if not sessions_df.empty:
                            # Report generation section
                            with st.container():
                                st.markdown("### Excel Performance Report")
                                st.markdown(
                                    "Comprehensive analysis including position, velocity, and timing data for all ranges.")

                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    selected_session_report = st.selectbox(
                                        "Select Session for Report",
                                        sessions_df['id'].tolist(),
                                        format_func=lambda
                                            x: f"Session {x} - {sessions_df[sessions_df['id'] == x]['username'].iloc[0]} - {pd.to_datetime(sessions_df[sessions_df['id'] == x]['session_date'].iloc[0]).strftime('%Y-%m-%d %H:%M')}",
                                        key="report_session"
                                    )

                                with col2:
                                    st.markdown("<br>", unsafe_allow_html=True)
                                    if st.button("📥 Export to Excel", use_container_width=True, type="primary"):
                                        with st.spinner("Generating report..."):
                                            # Get session and performance data
                                            session_data = \
                                            sessions_df[sessions_df['id'] == selected_session_report].iloc[0].to_dict()
                                            performance_df = pd.read_sql_query("""
                                                                               SELECT *
                                                                               FROM performance_data
                                                                               WHERE session_id = ?
                                                                               ORDER BY time_stamp
                                                                               """, conn,
                                                                               params=(selected_session_report,))

                                            # Generate Excel report
                                            excel_file = generate_excel_report(session_data, performance_df)

                                            # Create download button
                                            st.download_button(
                                                label="💾 Download Excel Report",
                                                data=excel_file,
                                                file_name=f"RunAnalytics_Report_{session_data['username']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                                use_container_width=True
                                            )

                                            st.success("✅ Report generated successfully!")

                                # Preview section
                                st.markdown("---")
                                st.markdown("### Report Preview")

                                # Get session details for preview
                                preview_session = sessions_df[sessions_df['id'] == selected_session_report].iloc[0]

                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown("**Session Information:**")
                                    st.write(f"- Runner: {preview_session['username']}")
                                    st.write(
                                        f"- Date: {pd.to_datetime(preview_session['session_date']).strftime('%Y-%m-%d %H:%M')}")
                                    st.write(f"- Total Distance: {preview_session['total_distance']:.1f} m")

                                with col2:
                                    st.markdown("**Performance Summary:**")
                                    st.write(f"- Max Velocity: {preview_session['max_velocity']:.3f} m/s")
                                    st.write(f"- Average Velocity: {preview_session['avg_velocity']:.3f} m/s")
                                    st.write(f"- Analysis Time: {preview_session['analysis_time']:.3f} s")

                                st.info(
                                    "📄 The Excel report includes detailed data for all segments, performance charts, and comprehensive analysis.")
                        else:
                            st.info("📑 No sessions available for report generation. Please process some videos first.")

                        conn.close()

                    # Tab 4: User Management (Admin only)
                    if st.session_state.user_role == "admin" and tab_users:
                        with tab_users:
                            st.markdown("## 👥 User Management")

                            col1, col2 = st.columns(2)

                            with col1:
                                st.markdown("### Create New User")

                                with st.form("create_user_form"):
                                    new_username = st.text_input("Username", placeholder="Enter username")
                                    new_password = st.text_input("Password", type="password",
                                                                 placeholder="Enter password")
                                    confirm_password = st.text_input("Confirm Password", type="password",
                                                                     placeholder="Confirm password")
                                    new_role = st.selectbox("Role", ["runner", "coach", "admin"])

                                    coach_id = None
                                    if new_role == "runner":
                                        # Get list of coaches
                                        conn = sqlite3.connect('running_analytics.db')
                                        coaches_df = pd.read_sql_query(
                                            "SELECT id, username FROM users WHERE role = 'coach'", conn)
                                        conn.close()

                                        if not coaches_df.empty:
                                            coach_id = st.selectbox(
                                                "Assign to Coach",
                                                coaches_df['id'].tolist(),
                                                format_func=lambda x:
                                                coaches_df[coaches_df['id'] == x]['username'].iloc[0]
                                            )
                                        else:
                                            st.warning("No coaches available. Please create a coach first.")

                                    submit = st.form_submit_button("Create User", use_container_width=True)

                                    if submit:
                                        if new_username and new_password and confirm_password:
                                            if new_password == confirm_password:
                                                if len(new_password) >= 6:
                                                    if create_user(new_username, new_password, new_role, coach_id):
                                                        st.success(f"✅ User '{new_username}' created successfully!")
                                                        time.sleep(1)
                                                        st.rerun()
                                                    else:
                                                        st.error("❌ Username already exists!")
                                                else:
                                                    st.error("❌ Password must be at least 6 characters long!")
                                            else:
                                                st.error("❌ Passwords do not match!")
                                        else:
                                            st.warning("⚠️ Please fill in all fields!")

                            with col2:
                                st.markdown("### Existing Users")

                                # Get users data
                                conn = sqlite3.connect('running_analytics.db')
                                users_df = pd.read_sql_query("""
                                                             SELECT u1.id,
                                                                    u1.username,
                                                                    u1.role,
                                                                    u2.username as coach_name,
                                                                    u1.created_at
                                                             FROM users u1
                                                                      LEFT JOIN users u2 ON u1.coach_id = u2.id
                                                             ORDER BY u1.role, u1.created_at DESC
                                                             """, conn)

                                # Display users by role
                                for role in ['admin', 'coach', 'runner']:
                                    role_users = users_df[users_df['role'] == role]
                                    if not role_users.empty:
                                        st.markdown(f"**{role.upper()}S ({len(role_users)})**")

                                        display_df = role_users[['username', 'coach_name', 'created_at']].copy()
                                        display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime(
                                            '%Y-%m-%d')
                                        display_df.columns = ['Username', 'Assigned Coach', 'Created Date']

                                        if role != 'runner':
                                            display_df = display_df[['Username', 'Created Date']]

                                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                                        st.markdown("")

                                conn.close()

                            # User statistics
                            st.markdown("---")
                            st.markdown("### User Statistics")

                            conn = sqlite3.connect('running_analytics.db')

                            # Get statistics
                            total_users = pd.read_sql_query("SELECT COUNT(*) as count FROM users", conn).iloc[0][
                                'count']
                            total_sessions = pd.read_sql_query("SELECT COUNT(*) as count FROM sessions", conn).iloc[0][
                                'count']

                            col1, col2, col3, col4 = st.columns(4)

                            with col1:
                                admin_count = \
                                pd.read_sql_query("SELECT COUNT(*) as count FROM users WHERE role = 'admin'",
                                                  conn).iloc[0]['count']
                                st.metric("Admins", admin_count)

                            with col2:
                                coach_count = \
                                pd.read_sql_query("SELECT COUNT(*) as count FROM users WHERE role = 'coach'",
                                                  conn).iloc[0]['count']
                                st.metric("Coaches", coach_count)

                            with col3:
                                runner_count = \
                                pd.read_sql_query("SELECT COUNT(*) as count FROM users WHERE role = 'runner'",
                                                  conn).iloc[0]['count']
                                st.metric("Runners", runner_count)

                            with col4:
                                st.metric("Total Sessions", total_sessions)

                            conn.close()

            if __name__ == "__main__":
                main()