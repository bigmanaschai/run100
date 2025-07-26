import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import os
import tempfile
from pathlib import Path
import json
import sqlite3
import hashlib
import io
from openpyxl import Workbook
from openpyxl.styles import Font, Fill, PatternFill, Border, Side, Alignment
from openpyxl.chart import LineChart, Reference
from openpyxl.chart.axis import DateAxis
import cv2

# Import custom modules
from auth import authenticate_user, create_user, get_user_role, get_runners_for_coach
from database import init_database, save_performance_data, get_performance_history
from video_processor import process_video, extract_runner_data
from report_generator import generate_excel_report, create_performance_charts

# Page configuration
st.set_page_config(
    page_title="RunAnalytics",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS with specified theme colors
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap');

    /* Global styles */
    html, body, [class*="css"] {
        font-family: 'Prompt', sans-serif !important;
    }

    /* Background */
    .stApp {
        background-color: rgb(247, 247, 247);
    }

    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: rgb(133, 72, 54) !important;
        font-family: 'Prompt', sans-serif !important;
    }

    /* Primary button */
    .stButton > button {
        background-color: rgb(255, 178, 44);
        color: rgb(0, 0, 0);
        border: none;
        font-family: 'Prompt', sans-serif !important;
        font-weight: 500;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        background-color: rgb(133, 72, 54);
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    /* Sidebar */
    .css-1d391kg {
        background-color: white;
        border-right: 2px solid rgb(255, 178, 44);
    }

    /* Cards */
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin: 10px 0;
        border-left: 4px solid rgb(255, 178, 44);
    }

    /* File uploader */
    .uploadedFile {
        background-color: white !important;
        border: 2px dashed rgb(255, 178, 44) !important;
        border-radius: 8px !important;
    }

    /* Success messages */
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 12px;
        border-radius: 8px;
        margin: 10px 0;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: white;
        padding: 10px;
        border-radius: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        color: rgb(133, 72, 54);
        font-family: 'Prompt', sans-serif !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: rgb(255, 178, 44) !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.user_role = None
    st.session_state.user_id = None

# Initialize database
init_database()


# Login page
def login_page():
    st.title("🏃 RunAnalytics")
    st.markdown("### Welcome to Running Performance Analysis System")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("#### Login")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("Login", use_container_width=True):
                user = authenticate_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_role = user['role']
                    st.session_state.user_id = user['id']
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")

        with col_btn2:
            if st.button("Register", use_container_width=True):
                st.session_state.show_register = True

        # Registration form
        if hasattr(st.session_state, 'show_register') and st.session_state.show_register:
            st.markdown("---")
            st.markdown("#### Register New User")
            new_username = st.text_input("New Username", key="reg_username")
            new_password = st.text_input("New Password", type="password", key="reg_password")
            new_email = st.text_input("Email", key="reg_email")
            role = st.selectbox("Role", ["runner", "coach", "admin"])

            if role == "runner":
                coach_username = st.text_input("Coach Username (if applicable)", key="coach_username")
            else:
                coach_username = None

            if st.button("Create Account"):
                if new_username and new_password and new_email:
                    success = create_user(new_username, new_password, new_email, role, coach_username)
                    if success:
                        st.success("Account created successfully! Please login.")
                        st.session_state.show_register = False
                        st.rerun()
                    else:
                        st.error("Username already exists")
                else:
                    st.error("Please fill all fields")


# Main application
def main_app():
    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown(f"**Role:** {st.session_state.user_role.title()}")
        st.markdown("---")

        if st.button("Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Main content
    st.title("My Running Performance")
    st.markdown("Track your running progress and performance metrics")

    # Create tabs
    if st.session_state.user_role == "admin":
        tabs = st.tabs(["Video Upload", "Performance Analysis", "Reports", "User Management"])
    else:
        tabs = st.tabs(["Video Upload", "Performance Analysis", "Reports"])

    # Video Upload Tab
    with tabs[0]:
        st.markdown("## 📹 Video Upload for Analysis")
        st.info("Upload videos for each range of the 100-meter track. Each camera captures 25 meters")

        # Runner selection for coach/admin
        if st.session_state.user_role in ["coach", "admin"]:
            if st.session_state.user_role == "coach":
                runners = get_runners_for_coach(st.session_state.user_id)
            else:
                runners = get_all_runners()  # Admin sees all runners

            runner_names = [r['username'] for r in runners]
            selected_runner = st.selectbox("Select Runner", runner_names)
            runner_id = next(r['id'] for r in runners if r['username'] == selected_runner)
        else:
            runner_id = st.session_state.user_id

        # Video upload sections
        col1, col2 = st.columns(2)
        uploaded_files = {}

        ranges = [
            ("Range 1", "0-25 meters", "range1"),
            ("Range 2", "25-50 meters", "range2"),
            ("Range 3", "50-75 meters", "range3"),
            ("Range 4", "75-100 meters", "range4")
        ]

        for i, (title, desc, key) in enumerate(ranges):
            with col1 if i % 2 == 0 else col2:
                with st.container():
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4>📹 {title}</h4>
                        <p>{desc}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    uploaded_file = st.file_uploader(
                        f"Choose video for {title}",
                        type=['mp4', 'avi', 'mov'],
                        key=f"upload_{key}"
                    )

                    if uploaded_file:
                        uploaded_files[key] = uploaded_file
                        st.success(f"✅ Video Uploaded for {title}")

        # Process videos button
        if len(uploaded_files) == 4:
            if st.button("🚀 Process Videos", use_container_width=True):
                with st.spinner("Processing videos... This may take a few minutes"):
                    # Save videos temporarily
                    temp_dir = tempfile.mkdtemp()
                    video_paths = {}

                    for key, file in uploaded_files.items():
                        video_path = os.path.join(temp_dir, f"{key}_{file.name}")
                        with open(video_path, "wb") as f:
                            f.write(file.getbuffer())
                        video_paths[key] = video_path

                    # Process videos and extract data
                    performance_data = process_videos_pipeline(video_paths, runner_id)

                    # Save to database
                    save_performance_data(runner_id, performance_data)

                    # Clean up temp files
                    for path in video_paths.values():
                        os.remove(path)
                    os.rmdir(temp_dir)

                    st.success("✅ Videos processed successfully!")
                    st.session_state.latest_performance = performance_data
        else:
            st.warning("Please upload all 4 videos to proceed")

    # Performance Analysis Tab
    with tabs[1]:
        st.markdown("## 📊 Performance Analysis")

        # Get performance data
        if st.session_state.user_role in ["coach", "admin"]:
            if st.session_state.user_role == "coach":
                runners = get_runners_for_coach(st.session_state.user_id)
            else:
                runners = get_all_runners()

            runner_names = [r['username'] for r in runners]
            selected_runner = st.selectbox("Select Runner for Analysis", runner_names, key="analysis_runner")
            runner_id = next(r['id'] for r in runners if r['username'] == selected_runner)
        else:
            runner_id = st.session_state.user_id

        # Get latest performance data
        performance_history = get_performance_history(runner_id)

        if performance_history:
            latest_performance = performance_history[0]

            # Display metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Max Velocity",
                    f"{latest_performance['max_velocity']:.3f} m/s",
                    "Peak speed achieved"
                )

            with col2:
                st.metric(
                    "Avg Velocity",
                    f"{latest_performance['avg_velocity']:.3f} m/s",
                    "Average speed"
                )

            with col3:
                st.metric(
                    "Total Distance",
                    f"{latest_performance['total_distance']:.1f} m",
                    "Distance covered"
                )

            with col4:
                st.metric(
                    "Analysis Time",
                    f"{latest_performance['total_time']:.3f} s",
                    "Total analysis duration"
                )

            # Visualizations
            col1, col2 = st.columns(2)

            with col1:
                # Position vs Time chart
                fig_pos = create_position_chart(latest_performance['position_data'])
                st.plotly_chart(fig_pos, use_container_width=True)

            with col2:
                # Velocity vs Time chart
                fig_vel = create_velocity_chart(latest_performance['velocity_data'])
                st.plotly_chart(fig_vel, use_container_width=True)

            # Detailed analysis
            st.markdown("### Detailed Analysis by Range")

            for i, range_name in enumerate(["0-25m", "25-50m", "50-75m", "75-100m"]):
                with st.expander(f"Range {i + 1}: {range_name}"):
                    range_data = latest_performance['range_data'][i]
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Max Speed", f"{range_data['max_speed']:.3f} m/s")
                    with col2:
                        st.metric("Avg Speed", f"{range_data['avg_speed']:.3f} m/s")
                    with col3:
                        st.metric("Time", f"{range_data['time']:.3f} s")
        else:
            st.info("No performance data available. Please upload and process videos first.")

    # Reports Tab
    with tabs[2]:
        st.markdown("## 📑 Performance Reports")
        st.markdown("Generate and download detailed performance analysis reports.")

        with st.container():
            st.markdown("""
            <div class="metric-card">
                <h3>Excel Performance Report</h3>
                <p>Comprehensive analysis including position, velocity, and timing data for all ranges.</p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("📥 Export to Excel", use_container_width=True):
                if hasattr(st.session_state, 'latest_performance'):
                    excel_buffer = generate_excel_report(st.session_state.latest_performance)

                    st.download_button(
                        label="📥 Download Excel Report",
                        data=excel_buffer,
                        file_name=f"running_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("No performance data available. Please process videos first.")

    # Admin Tab
    if st.session_state.user_role == "admin" and len(tabs) > 3:
        with tabs[3]:
            st.markdown("## 👥 User Management")
            # Add user management functionality here


# Helper functions
def process_videos_pipeline(video_paths, runner_id):
    """Process all videos and extract performance data"""
    all_data = {
        'position_data': [],
        'velocity_data': [],
        'range_data': [],
        'max_velocity': 0,
        'avg_velocity': 0,
        'total_distance': 0,
        'total_time': 0
    }

    # Process each video
    for i, (key, path) in enumerate(video_paths.items()):
        # Extract data from video (simplified for demo)
        data = extract_runner_data(path)
        all_data['range_data'].append(data)
        all_data['position_data'].extend(data['positions'])
        all_data['velocity_data'].extend(data['velocities'])

    # Calculate overall metrics
    velocities = [v for v in all_data['velocity_data'] if v > 0]
    all_data['max_velocity'] = max(velocities) if velocities else 0
    all_data['avg_velocity'] = np.mean(velocities) if velocities else 0
    all_data['total_distance'] = 100  # Fixed for 100m track
    all_data['total_time'] = sum(r['time'] for r in all_data['range_data'])

    return all_data


def create_position_chart(position_data):
    """Create position vs time chart"""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=position_data['time'],
        y=position_data['position'],
        mode='lines+markers',
        line=dict(color='rgb(255, 178, 44)', width=3),
        marker=dict(size=8, color='rgb(133, 72, 54)')
    ))

    fig.update_layout(
        title="Position vs Time",
        xaxis_title="Time (s)",
        yaxis_title="Position (m)",
        plot_bgcolor='white',
        paper_bgcolor='rgb(247, 247, 247)',
        font=dict(family="Prompt")
    )

    return fig


def create_velocity_chart(velocity_data):
    """Create velocity vs time chart"""
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=velocity_data['time'],
        y=velocity_data['velocity'],
        marker_color='rgb(133, 72, 54)'
    ))

    fig.update_layout(
        title="Velocity vs Time",
        xaxis_title="Time (s)",
        yaxis_title="Velocity (m/s)",
        plot_bgcolor='white',
        paper_bgcolor='rgb(247, 247, 247)',
        font=dict(family="Prompt")
    )

    return fig


def get_all_runners():
    """Get all runners (for admin)"""
    conn = sqlite3.connect('runanalytics.db')
    cursor = conn.cursor()

    cursor.execute("SELECT id, username FROM users WHERE role = 'runner'")
    runners = [{'id': row[0], 'username': row[1]} for row in cursor.fetchall()]

    conn.close()
    return runners


# Main execution
if __name__ == "__main__":
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()