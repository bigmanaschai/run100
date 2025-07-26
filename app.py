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
from openpyxl.utils import get_column_letter

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


# Database functions
def hash_password(password):
    """Hash password using SHA-256"""
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
                       video_paths
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

    # Range performance table
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS range_performance
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       performance_id
                       INTEGER
                       NOT
                       NULL,
                       range_number
                       INTEGER
                       NOT
                       NULL,
                       range_name
                       TEXT
                       NOT
                       NULL,
                       max_speed
                       REAL,
                       avg_speed
                       REAL,
                       time_taken
                       REAL,
                       distance
                       REAL,
                       FOREIGN
                       KEY
                   (
                       performance_id
                   ) REFERENCES performance_data
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
    """Authenticate user and return user info if successful"""
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


def create_user(username, password, email, role, coach_username=None):
    """Create a new user"""
    conn = sqlite3.connect('runanalytics.db')
    cursor = conn.cursor()

    # Check if username already exists
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return False

    # Get coach ID if provided
    coach_id = None
    if coach_username and role == 'runner':
        cursor.execute("SELECT id FROM users WHERE username = ? AND role = 'coach'", (coach_username,))
        coach_result = cursor.fetchone()
        if coach_result:
            coach_id = coach_result[0]

    # Insert new user
    hashed_password = hash_password(password)
    cursor.execute("""
                   INSERT INTO users (username, password, email, role, coach_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   """, (username, hashed_password, email, role, coach_id, datetime.now()))

    conn.commit()
    conn.close()
    return True


def get_runners_for_coach(coach_id):
    """Get all runners assigned to a coach"""
    conn = sqlite3.connect('runanalytics.db')
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT id, username, email
                   FROM users
                   WHERE coach_id = ?
                     AND role = 'runner'
                   """, (coach_id,))

    runners = []
    for row in cursor.fetchall():
        runners.append({
            'id': row[0],
            'username': row[1],
            'email': row[2]
        })

    conn.close()
    return runners


def get_all_runners():
    """Get all runners (for admin)"""
    conn = sqlite3.connect('runanalytics.db')
    cursor = conn.cursor()

    cursor.execute("SELECT id, username FROM users WHERE role = 'runner'")
    runners = [{'id': row[0], 'username': row[1]} for row in cursor.fetchall()]

    conn.close()
    return runners


def save_performance_data(runner_id, performance_data):
    """Save performance data to database"""
    conn = sqlite3.connect('runanalytics.db')
    cursor = conn.cursor()

    # Insert main performance data
    cursor.execute("""
                   INSERT INTO performance_data (runner_id, max_velocity, avg_velocity, total_distance,
                                                 total_time, position_data, velocity_data, range_data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   """, (
                       runner_id,
                       performance_data['max_velocity'],
                       performance_data['avg_velocity'],
                       performance_data['total_distance'],
                       performance_data['total_time'],
                       json.dumps(performance_data.get('position_data', [])),
                       json.dumps(performance_data.get('velocity_data', [])),
                       json.dumps(performance_data.get('range_data', []))
                   ))

    performance_id = cursor.lastrowid

    # Insert range-specific data
    ranges = ["0-25m", "25-50m", "50-75m", "75-100m"]
    for i, range_data in enumerate(performance_data.get('range_data', [])):
        cursor.execute("""
                       INSERT INTO range_performance (performance_id, range_number, range_name,
                                                      max_speed, avg_speed, time_taken, distance)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       """, (
                           performance_id,
                           i + 1,
                           ranges[i],
                           range_data.get('max_speed', 0),
                           range_data.get('avg_speed', 0),
                           range_data.get('time', 0),
                           25  # Each range is 25 meters
                       ))

    conn.commit()
    conn.close()
    return performance_id


def get_performance_history(runner_id, limit=10):
    """Get performance history for a runner"""
    conn = sqlite3.connect('runanalytics.db')
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT id,
                          session_date,
                          max_velocity,
                          avg_velocity,
                          total_distance,
                          total_time,
                          position_data,
                          velocity_data,
                          range_data
                   FROM performance_data
                   WHERE runner_id = ?
                   ORDER BY session_date DESC LIMIT ?
                   """, (runner_id, limit))

    performances = []
    for row in cursor.fetchall():
        performances.append({
            'id': row[0],
            'session_date': row[1],
            'max_velocity': row[2],
            'avg_velocity': row[3],
            'total_distance': row[4],
            'total_time': row[5],
            'position_data': json.loads(row[6]) if row[6] else [],
            'velocity_data': json.loads(row[7]) if row[7] else [],
            'range_data': json.loads(row[8]) if row[8] else []
        })

    conn.close()
    return performances


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


# Video processing simulation (without OpenCV)
def simulate_video_processing(video_files):
    """Simulate video processing and return synthetic data"""
    # Generate realistic running data based on the sample files
    time_points = []
    positions = []
    velocities = []

    # Simulate data for 100m sprint
    total_time = 11.0 + np.random.normal(0, 0.5)  # Around 11 seconds

    # Generate time series data
    for i in range(4):  # 4 ranges
        range_time = total_time / 4 + np.random.normal(0, 0.2)
        t = np.linspace(i * range_time, (i + 1) * range_time, 30)
        time_points.extend(t)

        # Position data (accelerating then maintaining speed)
        for j, time in enumerate(t):
            if i == 0:  # First 25m - acceleration
                pos = 25 * (j / len(t)) ** 1.5 + i * 25
            else:  # Other ranges - more linear
                pos = 25 * (j / len(t)) + i * 25
            positions.append(pos)

            # Velocity data
            if j == 0:
                velocities.append(0)
            else:
                vel = (positions[-1] - positions[-2]) / (t[j] - t[j - 1])
                velocities.append(vel)

    # Process range data
    range_data = []
    for i in range(4):
        start_idx = i * 30
        end_idx = (i + 1) * 30
        range_vels = velocities[start_idx:end_idx]
        valid_vels = [v for v in range_vels if v > 0]

        range_data.append({
            'max_speed': max(valid_vels) if valid_vels else 0,
            'avg_speed': np.mean(valid_vels) if valid_vels else 0,
            'time': time_points[end_idx - 1] - time_points[start_idx],
            'distance': 25.0
        })

    # Overall metrics
    valid_velocities = [v for v in velocities if v > 0]

    return {
        'position_data': {'time': time_points, 'position': positions},
        'velocity_data': {'time': time_points, 'velocity': velocities},
        'range_data': range_data,
        'max_velocity': max(valid_velocities) if valid_velocities else 0,
        'avg_velocity': np.mean(valid_velocities) if valid_velocities else 0,
        'total_distance': 100,
        'total_time': time_points[-1]
    }


def generate_excel_report(performance_data):
    """Generate comprehensive Excel report"""
    wb = Workbook()

    # Define styles
    header_font = Font(name='Arial', size=14, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='855448', end_color='855448', fill_type='solid')

    subheader_font = Font(name='Arial', size=12, bold=True)
    subheader_fill = PatternFill(start_color='FFB22C', end_color='FFB22C', fill_type='solid')

    data_font = Font(name='Arial', size=10)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Sheet 1: Summary
    ws_summary = wb.active
    ws_summary.title = "Summary"

    # Add headers
    ws_summary['A1'] = "Running Performance Analysis Report"
    ws_summary['A1'].font = Font(name='Arial', size=16, bold=True, color='855448')
    ws_summary.merge_cells('A1:E1')

    ws_summary['A3'] = "Generated on:"
    ws_summary['B3'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Performance metrics
    ws_summary['A5'] = "Performance Metrics"
    ws_summary['A5'].font = header_font
    ws_summary['A5'].fill = header_fill
    ws_summary.merge_cells('A5:B5')

    metrics = [
        ("Max Velocity", f"{performance_data['max_velocity']:.3f} m/s"),
        ("Average Velocity", f"{performance_data['avg_velocity']:.3f} m/s"),
        ("Total Distance", f"{performance_data['total_distance']:.1f} m"),
        ("Total Time", f"{performance_data['total_time']:.3f} s"),
    ]

    row = 6
    for metric, value in metrics:
        ws_summary[f'A{row}'] = metric
        ws_summary[f'B{row}'] = value
        ws_summary[f'A{row}'].font = subheader_font
        ws_summary[f'B{row}'].font = data_font
        row += 1

    # Save to buffer
    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)

    return excel_buffer


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
                runners = get_all_runners()

            if runners:
                runner_names = [r['username'] for r in runners]
                selected_runner = st.selectbox("Select Runner", runner_names)
                runner_id = next(r['id'] for r in runners if r['username'] == selected_runner)
            else:
                st.warning("No runners available")
                runner_id = None
        else:
            runner_id = st.session_state.user_id

        if runner_id:
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
                        performance_data = simulate_video_processing(uploaded_files)

                        # Save to database
                        save_performance_data(runner_id, performance_data)

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

            if runners:
                runner_names = [r['username'] for r in runners]
                selected_runner = st.selectbox("Select Runner for Analysis", runner_names, key="analysis_runner")
                runner_id = next(r['id'] for r in runners if r['username'] == selected_runner)
            else:
                st.warning("No runners available")
                runner_id = None
        else:
            runner_id = st.session_state.user_id

        if runner_id:
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
                    fig_pos = go.Figure()
                    fig_pos.add_trace(go.Scatter(
                        x=latest_performance['position_data']['time'],
                        y=latest_performance['position_data']['position'],
                        mode='lines+markers',
                        line=dict(color='rgb(255, 178, 44)', width=3),
                        marker=dict(size=6, color='rgb(133, 72, 54)')
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
                        x=latest_performance['velocity_data']['time'][::10],
                        y=latest_performance['velocity_data']['velocity'][::10],
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

                # Detailed analysis
                st.markdown("### Detailed Analysis by Range")

                for i, range_name in enumerate(["0-25m", "25-50m", "50-75m", "75-100m"]):
                    with st.expander(f"Range {i + 1}: {range_name}"):
                        if i < len(latest_performance['range_data']):
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

            # Show all users
            conn = sqlite3.connect('runanalytics.db')
            df_users = pd.read_sql_query("""
                                         SELECT id, username, email, role, created_at
                                         FROM users
                                         ORDER BY created_at DESC
                                         """, conn)
            conn.close()

            st.dataframe(df_users, use_container_width=True)


# Main execution
if __name__ == "__main__":
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()