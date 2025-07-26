import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import os
import io
import json
import sqlite3
import hashlib
from pathlib import Path

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

    /* Cards */
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin: 10px 0;
        border-left: 4px solid rgb(255, 178, 44);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.user_role = None
    st.session_state.user_id = None


# Simple authentication functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def init_database():
    """Initialize database with required tables"""
    conn = sqlite3.connect('runanalytics.db')
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS users
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
                       email
                       TEXT
                       NOT
                       NULL,
                       role
                       TEXT
                       NOT
                       NULL
                       CHECK (
                       role
                       IN
                   (
                       'admin',
                       'coach',
                       'runner'
                   )),
                       coach_id INTEGER,
                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       FOREIGN KEY
                   (
                       coach_id
                   ) REFERENCES users
                   (
                       id
                   )
                       )
                   """)

    # Performance data table
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS performance_data
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
                       session_date
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       max_velocity
                       REAL,
                       avg_velocity
                       REAL,
                       total_distance
                       REAL,
                       total_time
                       REAL,
                       position_data
                       TEXT,
                       velocity_data
                       TEXT,
                       range_data
                       TEXT,
                       FOREIGN
                       KEY
                   (
                       runner_id
                   ) REFERENCES users
                   (
                       id
                   )
                       )
                   """)

    # Insert default admin user if not exists
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("""
                       INSERT INTO users (username, password, email, role)
                       VALUES (?, ?, ?, ?)
                       """, ('admin', hash_password('admin123'), 'admin@runanalytics.com', 'admin'))

    conn.commit()
    conn.close()


def authenticate_user(username, password):
    """Authenticate user"""
    conn = sqlite3.connect('runanalytics.db')
    cursor = conn.cursor()

    hashed_password = hash_password(password)

    cursor.execute("""
                   SELECT id, username, email, role
                   FROM users
                   WHERE username = ?
                     AND password = ?
                   """, (username, hashed_password))

    user = cursor.fetchone()
    conn.close()

    if user:
        return {
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'role': user[3]
        }
    return None


def create_user(username, password, email, role):
    """Create a new user"""
    conn = sqlite3.connect('runanalytics.db')
    cursor = conn.cursor()

    # Check if username already exists
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return False

    # Insert new user
    hashed_password = hash_password(password)
    cursor.execute("""
                   INSERT INTO users (username, password, email, role)
                   VALUES (?, ?, ?, ?)
                   """, (username, hashed_password, email, role))

    conn.commit()
    conn.close()
    return True


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

            if st.button("Create Account"):
                if new_username and new_password and new_email:
                    success = create_user(new_username, new_password, new_email, role)
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
    tabs = st.tabs(["Video Upload", "Performance Analysis", "Reports"])

    # Video Upload Tab
    with tabs[0]:
        st.markdown("## 📹 Video Upload for Analysis")
        st.info("Upload videos for each range of the 100-meter track. Each camera captures 25 meters")

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
                    # Simulate processing
                    import time
                    time.sleep(2)

                    # Generate sample data
                    performance_data = {
                        'max_velocity': 9.58,
                        'avg_velocity': 8.44,
                        'total_distance': 100,
                        'total_time': 11.85,
                        'position_data': {'time': list(np.linspace(0, 11.85, 50)),
                                          'position': list(np.linspace(0, 100, 50))},
                        'velocity_data': {'time': list(np.linspace(0, 11.85, 50)),
                                          'velocity': list(8 + 2 * np.sin(np.linspace(0, 2 * np.pi, 50)))},
                        'range_data': [
                            {'max_speed': 8.5, 'avg_speed': 7.2, 'time': 3.1},
                            {'max_speed': 9.8, 'avg_speed': 9.2, 'time': 2.8},
                            {'max_speed': 9.6, 'avg_speed': 9.1, 'time': 2.9},
                            {'max_speed': 9.2, 'avg_speed': 8.8, 'time': 3.05}
                        ]
                    }

                    st.success("✅ Videos processed successfully!")
                    st.session_state.latest_performance = performance_data
        else:
            st.warning("Please upload all 4 videos to proceed")

    # Performance Analysis Tab
    with tabs[1]:
        st.markdown("## 📊 Performance Analysis")

        if hasattr(st.session_state, 'latest_performance'):
            performance_data = st.session_state.latest_performance

            # Display metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Max Velocity",
                    f"{performance_data['max_velocity']:.3f} m/s",
                    "Peak speed achieved"
                )

            with col2:
                st.metric(
                    "Avg Velocity",
                    f"{performance_data['avg_velocity']:.3f} m/s",
                    "Average speed"
                )

            with col3:
                st.metric(
                    "Total Distance",
                    f"{performance_data['total_distance']:.1f} m",
                    "Distance covered"
                )

            with col4:
                st.metric(
                    "Analysis Time",
                    f"{performance_data['total_time']:.3f} s",
                    "Total analysis duration"
                )

            # Visualizations
            col1, col2 = st.columns(2)

            with col1:
                # Position vs Time chart
                fig_pos = go.Figure()
                fig_pos.add_trace(go.Scatter(
                    x=performance_data['position_data']['time'],
                    y=performance_data['position_data']['position'],
                    mode='lines+markers',
                    line=dict(color='rgb(255, 178, 44)', width=3),
                    marker=dict(size=8, color='rgb(133, 72, 54)')
                ))

                fig_pos.update_layout(
                    title="Position vs Time",
                    xaxis_title="Time (s)",
                    yaxis_title="Position (m)",
                    plot_bgcolor='white',
                    paper_bgcolor='rgb(247, 247, 247)',
                    font=dict(family="Prompt")
                )

                st.plotly_chart(fig_pos, use_container_width=True)

            with col2:
                # Velocity vs Time chart
                fig_vel = go.Figure()
                fig_vel.add_trace(go.Bar(
                    x=performance_data['velocity_data']['time'][::5],  # Sample every 5th point
                    y=performance_data['velocity_data']['velocity'][::5],
                    marker_color='rgb(133, 72, 54)'
                ))

                fig_vel.update_layout(
                    title="Velocity vs Time",
                    xaxis_title="Time (s)",
                    yaxis_title="Velocity (m/s)",
                    plot_bgcolor='white',
                    paper_bgcolor='rgb(247, 247, 247)',
                    font=dict(family="Prompt")
                )

                st.plotly_chart(fig_vel, use_container_width=True)
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
                    st.info("Excel export feature will be available after video processing module is installed.")
                else:
                    st.warning("No performance data available. Please process videos first.")


# Main execution
if __name__ == "__main__":
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()