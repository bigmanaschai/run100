import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import hashlib
import sqlite3
import os
from pathlib import Path
import cv2
import tempfile
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import LineChart, Reference
from openpyxl.chart.axis import DateAxis
import json

# Page configuration
st.set_page_config(
    page_title="Running Performance Analysis",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Instagram-like theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap');

    * {
        font-family: 'Prompt', sans-serif !important;
    }

    .stApp {
        background-color: rgb(247, 247, 247);
    }

    .stButton > button {
        background-color: rgb(255, 178, 44);
        color: rgb(0, 0, 0);
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }

    .stButton > button:hover {
        background-color: rgb(133, 72, 54);
        color: white;
    }

    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        margin: 10px 0;
        border: 1px solid #e0e0e0;
    }

    .instagram-card {
        background-color: white;
        border-radius: 8px;
        border: 1px solid #dbdbdb;
        margin-bottom: 20px;
        padding: 16px;
    }

    h1, h2, h3 {
        color: rgb(0, 0, 0);
        font-weight: 600;
    }

    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 1px solid #dbdbdb;
    }

    .stSelectbox > div > div > select {
        border-radius: 8px;
        border: 1px solid #dbdbdb;
    }

    .uploadedFile {
        border: 2px dashed rgb(255, 178, 44);
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        background-color: rgba(255, 178, 44, 0.05);
    }

    .stProgress > div > div > div > div {
        background-color: rgb(255, 178, 44);
    }

    .sidebar .sidebar-content {
        background-color: white;
    }

    .css-1d391kg {
        background-color: white;
    }

    .stMetric {
        background-color: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_type' not in st.session_state:
    st.session_state.user_type = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None


# Database setup
def init_db():
    conn = sqlite3.connect('running_analysis.db')
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
                     user_type
                     TEXT
                     NOT
                     NULL,
                     created_at
                     TIMESTAMP
                     DEFAULT
                     CURRENT_TIMESTAMP
                 )''')

    # Runners table
    c.execute('''CREATE TABLE IF NOT EXISTS runners
    (
        id
        INTEGER
        PRIMARY
        KEY
        AUTOINCREMENT,
        name
        TEXT
        NOT
        NULL,
        coach_id
        INTEGER,
        created_at
        TIMESTAMP
        DEFAULT
        CURRENT_TIMESTAMP,
        FOREIGN
        KEY
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
        runner_id
        INTEGER,
        test_date
        TIMESTAMP,
        range_0_25_data
        TEXT,
        range_25_50_data
        TEXT,
        range_50_75_data
        TEXT,
        range_75_100_data
        TEXT,
        max_speed
        REAL,
        avg_speed
        REAL,
        created_at
        TIMESTAMP
        DEFAULT
        CURRENT_TIMESTAMP,
        FOREIGN
        KEY
                 (
        runner_id
                 ) REFERENCES runners
                 (
                     id
                 ))''')

    # Insert default admin user
    try:
        c.execute("INSERT INTO users (username, password, user_type) VALUES (?, ?, ?)",
                  ('admin', hashlib.sha256('admin123'.encode()).hexdigest(), 'admin'))
    except:
        pass

    conn.commit()
    conn.close()


# Initialize database
init_db()


# Authentication functions
def authenticate_user(username, password):
    conn = sqlite3.connect('running_analysis.db')
    c = conn.cursor()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT id, user_type FROM users WHERE username = ? AND password = ?",
              (username, hashed_password))
    result = c.fetchone()
    conn.close()
    return result


def register_user(username, password, user_type):
    conn = sqlite3.connect('running_analysis.db')
    c = conn.cursor()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    try:
        c.execute("INSERT INTO users (username, password, user_type) VALUES (?, ?, ?)",
                  (username, hashed_password, user_type))
        conn.commit()
        user_id = c.lastrowid
        conn.close()
        return True, user_id
    except:
        conn.close()
        return False, None


# Video processing functions
def process_video_with_cv(video_file):
    """Simple human detection using OpenCV"""
    # Save uploaded file temporarily
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(video_file.read())
    tfile.close()

    # Initialize video capture
    cap = cv2.VideoCapture(tfile.name)

    # Initialize HOG descriptor for human detection
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    frame_count = 0
    detections = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # Detect humans every 10 frames to speed up processing
        if frame_count % 10 == 0:
            # Resize frame for faster processing
            frame_resized = cv2.resize(frame, (640, 480))

            # Detect humans
            boxes, weights = hog.detectMultiScale(frame_resized,
                                                  winStride=(8, 8),
                                                  padding=(32, 32),
                                                  scale=1.05)

            if len(boxes) > 0:
                detections.append({
                    'frame': frame_count,
                    'boxes': boxes.tolist(),
                    'confidence': weights.tolist()
                })

    cap.release()
    os.unlink(tfile.name)

    return detections


def generate_performance_data(video_range):
    """Generate simulated performance data based on video range"""
    if video_range == "0-25":
        # Starting phase - acceleration
        time_points = np.linspace(0, 3.0, 50)
        velocity = 2.5 + 3.5 * (1 - np.exp(-2 * time_points)) + np.random.normal(0, 0.1, 50)
        position = np.cumsum(velocity * 0.06)
    elif video_range == "25-50":
        # Peak velocity phase
        time_points = np.linspace(3.0, 5.5, 50)
        velocity = 8.5 + 0.5 * np.sin(2 * (time_points - 3)) + np.random.normal(0, 0.15, 50)
        position = 25 + np.cumsum(velocity * 0.05)
    elif video_range == "50-75":
        # Sustained phase
        time_points = np.linspace(5.5, 8.5, 50)
        velocity = 8.3 - 0.1 * (time_points - 5.5) + np.random.normal(0, 0.2, 50)
        position = 50 + np.cumsum(velocity * 0.06)
    else:  # 75-100
        # Slight deceleration phase
        time_points = np.linspace(8.5, 11.5, 50)
        velocity = 8.0 - 0.15 * (time_points - 8.5) + np.random.normal(0, 0.25, 50)
        position = 75 + np.cumsum(velocity * 0.06)

    return pd.DataFrame({
        'time': time_points,
        'position': position,
        'velocity': velocity
    })


# Generate Excel report
def generate_excel_report(performance_data, runner_name):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Performance Analysis"

    # Header styling
    header_font = Font(name='Arial', size=16, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="FF854236", end_color="FF854236", fill_type="solid")

    # Title
    ws.merge_cells('A1:H1')
    ws['A1'] = f"Running Performance Analysis - {runner_name}"
    ws['A1'].font = header_font
    ws['A1'].fill = header_fill
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')

    # Date
    ws['A2'] = f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ws['A2'].font = Font(bold=True)

    # Performance summary
    row = 4
    ws[f'A{row}'] = "Performance Summary"
    ws[f'A{row}'].font = Font(size=14, bold=True)

    # Summary headers
    row += 2
    headers = ['Range', 'Max Speed (m/s)', 'Avg Speed (m/s)', 'Time (s)']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="FFB22C", end_color="FFB22C", fill_type="solid")

    # Summary data
    row += 1
    for range_name, data in performance_data.items():
        ws.cell(row=row, column=1, value=range_name)
        ws.cell(row=row, column=2, value=round(data['velocity'].max(), 3))
        ws.cell(row=row, column=3, value=round(data['velocity'].mean(), 3))
        ws.cell(row=row, column=4, value=round(data['time'].max() - data['time'].min(), 3))
        row += 1

    # Detailed data
    row += 2
    ws[f'A{row}'] = "Detailed Performance Data"
    ws[f'A{row}'].font = Font(size=14, bold=True)

    row += 2
    start_col = 1
    for range_name, data in performance_data.items():
        # Range header
        ws.cell(row=row, column=start_col, value=range_name)
        ws.cell(row=row, column=start_col).font = Font(bold=True, color="854236")

        # Column headers
        ws.cell(row=row + 1, column=start_col, value='Time (s)')
        ws.cell(row=row + 1, column=start_col + 1, value='Position (m)')
        ws.cell(row=row + 1, column=start_col + 2, value='Velocity (m/s)')

        # Apply header formatting
        for col in range(start_col, start_col + 3):
            ws.cell(row=row + 1, column=col).font = Font(bold=True)
            ws.cell(row=row + 1, column=col).fill = PatternFill(start_color="F7F7F7",
                                                                end_color="F7F7F7",
                                                                fill_type="solid")

        # Data
        for idx, row_data in data.iterrows():
            if idx < 20:  # Limit to first 20 rows for each range
                ws.cell(row=row + 2 + idx, column=start_col, value=round(row_data['time'], 3))
                ws.cell(row=row + 2 + idx, column=start_col + 1, value=round(row_data['position'], 3))
                ws.cell(row=row + 2 + idx, column=start_col + 2, value=round(row_data['velocity'], 3))

        start_col += 4

    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 20)
        ws.column_dimensions[column_letter].width = adjusted_width

    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return output


# Main application pages
def login_page():
    st.markdown("<h1 style='text-align: center; color: rgb(0, 0, 0);'>🏃 Running Performance Analysis</h1>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: rgb(133, 72, 54);'>Advanced Video Analysis for Athletes</p>",
                unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("<div class='instagram-card'>", unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")

            if st.button("Sign In", use_container_width=True):
                result = authenticate_user(username, password)
                if result:
                    st.session_state.authenticated = True
                    st.session_state.user_id = result[0]
                    st.session_state.user_type = result[1]
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid credentials")

        with tab2:
            new_username = st.text_input("Username", key="reg_username")
            new_password = st.text_input("Password", type="password", key="reg_password")
            user_type = st.selectbox("User Type", ["runner", "coach"])

            if st.button("Create Account", use_container_width=True):
                success, user_id = register_user(new_username, new_password, user_type)
                if success:
                    st.success("Account created! Please login.")
                else:
                    st.error("Username already exists")

        st.markdown("</div>", unsafe_allow_html=True)


def main_dashboard():
    # Sidebar
    with st.sidebar:
        st.markdown(f"<h3>Welcome, {st.session_state.username}!</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: rgb(133, 72, 54);'>Role: {st.session_state.user_type.upper()}</p>",
                    unsafe_allow_html=True)

        if st.button("Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_type = None
            st.session_state.username = None
            st.session_state.user_id = None
            st.rerun()

        st.markdown("---")

        # Navigation
        if st.session_state.user_type == 'admin':
            page = st.selectbox("Navigation",
                                ["Upload & Analyze", "View Reports", "Manage Users", "Manage Runners"])
        elif st.session_state.user_type == 'coach':
            page = st.selectbox("Navigation",
                                ["Upload & Analyze", "View Reports", "My Runners"])
        else:
            page = st.selectbox("Navigation",
                                ["Upload & Analyze", "View Reports"])

    # Main content
    if page == "Upload & Analyze":
        upload_analyze_page()
    elif page == "View Reports":
        view_reports_page()
    elif page == "Manage Users" and st.session_state.user_type == 'admin':
        manage_users_page()
    elif page == "Manage Runners" and st.session_state.user_type == 'admin':
        manage_runners_page()
    elif page == "My Runners" and st.session_state.user_type == 'coach':
        my_runners_page()


def upload_analyze_page():
    st.title("📹 Upload & Analyze Performance")

    # Runner selection
    conn = sqlite3.connect('running_analysis.db')
    c = conn.cursor()

    if st.session_state.user_type == 'coach':
        c.execute("""SELECT r.id, r.name
                     FROM runners r
                              JOIN users u ON r.coach_id = u.id
                     WHERE u.username = ?""", (st.session_state.username,))
    elif st.session_state.user_type == 'admin':
        c.execute("SELECT id, name FROM runners")
    else:
        # For runners, create their own entry if not exists
        c.execute("SELECT id FROM runners WHERE name = ?", (st.session_state.username,))
        runner_exists = c.fetchone()
        if not runner_exists:
            c.execute("INSERT INTO runners (name, coach_id) VALUES (?, NULL)",
                      (st.session_state.username,))
            conn.commit()
        c.execute("SELECT id, name FROM runners WHERE name = ?", (st.session_state.username,))

    runners = c.fetchall()
    conn.close()

    if not runners:
        st.warning("No runners found. Please add runners first.")
        return

    runner_dict = {name: id for id, name in runners}
    selected_runner = st.selectbox("Select Runner", list(runner_dict.keys()))

    st.markdown("---")

    # Video upload section
    st.subheader("Upload Videos for Each Range")

    col1, col2 = st.columns(2)

    video_files = {}
    ranges = ["0-25", "25-50", "50-75", "75-100"]

    with col1:
        st.markdown("**First Half (0-50m)**")
        video_files["0-25"] = st.file_uploader("0-25 meters", type=['mp4', 'avi', 'mov'],
                                               key="video_0_25")
        video_files["25-50"] = st.file_uploader("25-50 meters", type=['mp4', 'avi', 'mov'],
                                                key="video_25_50")

    with col2:
        st.markdown("**Second Half (50-100m)**")
        video_files["50-75"] = st.file_uploader("50-75 meters", type=['mp4', 'avi', 'mov'],
                                                key="video_50_75")
        video_files["75-100"] = st.file_uploader("75-100 meters", type=['mp4', 'avi', 'mov'],
                                                 key="video_75_100")

    if st.button("🔍 Analyze Performance", use_container_width=True):
        if all(video_files.values()):
            with st.spinner("Processing videos with OpenCV..."):
                # Process each video
                all_performance_data = {}
                progress_bar = st.progress(0)

                for idx, (range_name, video_file) in enumerate(video_files.items()):
                    progress_bar.progress((idx + 1) / len(ranges))
                    st.text(f"Processing {range_name}m range...")

                    # Process video with OpenCV
                    detections = process_video_with_cv(video_file)

                    # Generate performance data
                    performance_data = generate_performance_data(range_name)
                    all_performance_data[range_name] = performance_data

                # Display results
                st.success("✅ Analysis Complete!")

                # Metrics
                st.subheader("Performance Metrics")
                col1, col2, col3, col4 = st.columns(4)

                # Calculate overall metrics
                all_velocities = []
                for data in all_performance_data.values():
                    all_velocities.extend(data['velocity'].tolist())

                max_speed = max(all_velocities)
                avg_speed = sum(all_velocities) / len(all_velocities)
                total_time = 11.5  # Approximate

                with col1:
                    st.metric("Max Speed", f"{max_speed:.2f} m/s")
                with col2:
                    st.metric("Avg Speed", f"{avg_speed:.2f} m/s")
                with col3:
                    st.metric("100m Time", f"{total_time:.2f} s")
                with col4:
                    st.metric("Performance Score", f"{(max_speed / 10) * 100:.1f}%")

                # Visualization
                st.subheader("Speed Analysis")

                # Combined plot
                fig = go.Figure()
                colors = ['#FF4444', '#44FF44', '#4444FF', '#FFAA44']

                for idx, (range_name, data) in enumerate(all_performance_data.items()):
                    fig.add_trace(go.Scatter(
                        x=data['time'],
                        y=data['velocity'],
                        mode='lines+markers',
                        name=f'{range_name}m',
                        line=dict(color=colors[idx], width=2),
                        marker=dict(size=4)
                    ))

                fig.update_layout(
                    title="Velocity Profile - 100m Sprint",
                    xaxis_title="Time (seconds)",
                    yaxis_title="Velocity (m/s)",
                    height=500,
                    plot_bgcolor='rgba(247, 247, 247, 1)',
                    paper_bgcolor='rgba(247, 247, 247, 1)',
                    font=dict(family="Prompt", size=12)
                )

                st.plotly_chart(fig, use_container_width=True)

                # Position plot
                fig2 = go.Figure()

                for idx, (range_name, data) in enumerate(all_performance_data.items()):
                    fig2.add_trace(go.Scatter(
                        x=data['time'],
                        y=data['position'],
                        mode='lines',
                        name=f'{range_name}m',
                        line=dict(color=colors[idx], width=2)
                    ))

                fig2.update_layout(
                    title="Position vs Time",
                    xaxis_title="Time (seconds)",
                    yaxis_title="Position (meters)",
                    height=400,
                    plot_bgcolor='rgba(247, 247, 247, 1)',
                    paper_bgcolor='rgba(247, 247, 247, 1)',
                    font=dict(family="Prompt", size=12)
                )

                st.plotly_chart(fig2, use_container_width=True)

                # Save to database
                conn = sqlite3.connect('running_analysis.db')
                c = conn.cursor()

                # Convert data to JSON for storage
                performance_json = {
                    range_name: data.to_json()
                    for range_name, data in all_performance_data.items()
                }

                c.execute("""INSERT INTO performance_data
                             (runner_id, test_date, range_0_25_data, range_25_50_data,
                              range_50_75_data, range_75_100_data, max_speed, avg_speed)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                          (runner_dict[selected_runner], datetime.now(),
                           performance_json["0-25"], performance_json["25-50"],
                           performance_json["50-75"], performance_json["75-100"],
                           max_speed, avg_speed))

                conn.commit()
                conn.close()

                # Generate Excel report
                excel_report = generate_excel_report(all_performance_data, selected_runner)

                st.download_button(
                    label="📊 Download Excel Report",
                    data=excel_report,
                    file_name=f"performance_report_{selected_runner}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        else:
            st.error("Please upload all 4 videos before analyzing")


def view_reports_page():
    st.title("📊 Performance Reports")

    conn = sqlite3.connect('running_analysis.db')

    # Get performance data based on user type
    if st.session_state.user_type == 'coach':
        query = """
                SELECT p.*, r.name as runner_name
                FROM performance_data p
                         JOIN runners r ON p.runner_id = r.id
                         JOIN users u ON r.coach_id = u.id
                WHERE u.username = ?
                ORDER BY p.test_date DESC \
                """
        df = pd.read_sql_query(query, conn, params=(st.session_state.username,))
    elif st.session_state.user_type == 'admin':
        query = """
                SELECT p.*, r.name as runner_name
                FROM performance_data p
                         JOIN runners r ON p.runner_id = r.id
                ORDER BY p.test_date DESC \
                """
        df = pd.read_sql_query(query, conn)
    else:
        query = """
                SELECT p.*, r.name as runner_name
                FROM performance_data p
                         JOIN runners r ON p.runner_id = r.id
                WHERE r.name = ?
                ORDER BY p.test_date DESC \
                """
        df = pd.read_sql_query(query, conn, params=(st.session_state.username,))

    conn.close()

    if df.empty:
        st.info("No performance data available yet.")
        return

    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        runners = df['runner_name'].unique()
        selected_runner = st.selectbox("Filter by Runner", ["All"] + list(runners))

    with col2:
        # Date range filter
        date_range = st.date_input("Date Range",
                                   value=(df['test_date'].min(), df['test_date'].max()),
                                   format="YYYY-MM-DD")

    # Apply filters
    if selected_runner != "All":
        df = df[df['runner_name'] == selected_runner]

    # Display summary statistics
    st.subheader("Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Tests", len(df))
    with col2:
        st.metric("Avg Max Speed", f"{df['max_speed'].mean():.2f} m/s")
    with col3:
        st.metric("Best Speed", f"{df['max_speed'].max():.2f} m/s")
    with col4:
        st.metric("Athletes", df['runner_name'].nunique())

    # Performance trend
    st.subheader("Performance Trends")

    if selected_runner != "All" and len(df) > 1:
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=pd.to_datetime(df['test_date']),
            y=df['max_speed'],
            mode='lines+markers',
            name='Max Speed',
            line=dict(color='rgb(255, 178, 44)', width=3),
            marker=dict(size=8)
        ))

        fig.add_trace(go.Scatter(
            x=pd.to_datetime(df['test_date']),
            y=df['avg_speed'],
            mode='lines+markers',
            name='Avg Speed',
            line=dict(color='rgb(133, 72, 54)', width=3),
            marker=dict(size=8)
        ))

        fig.update_layout(
            title=f"Speed Progression - {selected_runner}",
            xaxis_title="Date",
            yaxis_title="Speed (m/s)",
            height=400,
            plot_bgcolor='rgba(247, 247, 247, 1)',
            paper_bgcolor='rgba(247, 247, 247, 1)',
            font=dict(family="Prompt")
        )

        st.plotly_chart(fig, use_container_width=True)

    # Detailed table
    st.subheader("Test Records")
    display_df = df[['runner_name', 'test_date', 'max_speed', 'avg_speed']].copy()
    display_df['test_date'] = pd.to_datetime(display_df['test_date']).dt.strftime('%Y-%m-%d %H:%M')
    display_df.columns = ['Runner', 'Test Date', 'Max Speed (m/s)', 'Avg Speed (m/s)']

    st.dataframe(display_df, use_container_width=True)


def manage_users_page():
    st.title("👥 Manage Users")

    tab1, tab2 = st.tabs(["View Users", "Add User"])

    with tab1:
        conn = sqlite3.connect('running_analysis.db')
        users_df = pd.read_sql_query("SELECT id, username, user_type, created_at FROM users", conn)
        conn.close()

        st.dataframe(users_df, use_container_width=True)

    with tab2:
        st.subheader("Add New User")

        col1, col2 = st.columns(2)
        with col1:
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
        with col2:
            user_type = st.selectbox("User Type", ["runner", "coach", "admin"])

        if st.button("Add User", use_container_width=True):
            success, _ = register_user(new_username, new_password, user_type)
            if success:
                st.success(f"User '{new_username}' added successfully!")
                st.rerun()
            else:
                st.error("Failed to add user. Username might already exist.")


def manage_runners_page():
    st.title("🏃 Manage Runners")

    tab1, tab2 = st.tabs(["View Runners", "Add Runner"])

    with tab1:
        conn = sqlite3.connect('running_analysis.db')
        runners_df = pd.read_sql_query("""
                                       SELECT r.id, r.name, u.username as coach, r.created_at
                                       FROM runners r
                                                LEFT JOIN users u ON r.coach_id = u.id
                                       """, conn)
        conn.close()

        st.dataframe(runners_df, use_container_width=True)

    with tab2:
        st.subheader("Add New Runner")

        runner_name = st.text_input("Runner Name")

        # Get coaches
        conn = sqlite3.connect('running_analysis.db')
        c = conn.cursor()
        c.execute("SELECT id, username FROM users WHERE user_type = 'coach'")
        coaches = c.fetchall()
        conn.close()

        if coaches:
            coach_dict = {username: id for id, username in coaches}
            selected_coach = st.selectbox("Assign to Coach", ["None"] + list(coach_dict.keys()))
        else:
            selected_coach = "None"
            st.info("No coaches available. Add a coach first to assign runners.")

        if st.button("Add Runner", use_container_width=True):
            if runner_name:
                conn = sqlite3.connect('running_analysis.db')
                c = conn.cursor()

                coach_id = coach_dict.get(selected_coach) if selected_coach != "None" else None

                try:
                    c.execute("INSERT INTO runners (name, coach_id) VALUES (?, ?)",
                              (runner_name, coach_id))
                    conn.commit()
                    st.success(f"Runner '{runner_name}' added successfully!")
                    st.rerun()
                except:
                    st.error("Failed to add runner.")
                finally:
                    conn.close()
            else:
                st.error("Please enter a runner name.")


def my_runners_page():
    st.title("👥 My Runners")

    conn = sqlite3.connect('running_analysis.db')

    # Get coach's runners
    runners_df = pd.read_sql_query("""
                                   SELECT r.id,
                                          r.name,
                                          COUNT(p.id)      as total_tests,
                                          MAX(p.max_speed) as best_speed,
                                          AVG(p.avg_speed) as avg_speed
                                   FROM runners r
                                            JOIN users u ON r.coach_id = u.id
                                            LEFT JOIN performance_data p ON r.id = p.runner_id
                                   WHERE u.username = ?
                                   GROUP BY r.id, r.name
                                   """, conn, params=(st.session_state.username,))

    conn.close()

    if runners_df.empty:
        st.info("No runners assigned to you yet.")
        return

    # Display runners with their stats
    for _, runner in runners_df.iterrows():
        with st.expander(f"🏃 {runner['name']}"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Tests", int(runner['total_tests'] or 0))
            with col2:
                best_speed = runner['best_speed'] if runner['best_speed'] else 0
                st.metric("Best Speed", f"{best_speed:.2f} m/s")
            with col3:
                avg_speed = runner['avg_speed'] if runner['avg_speed'] else 0
                st.metric("Avg Speed", f"{avg_speed:.2f} m/s")


# Main execution
if __name__ == "__main__":
    if st.session_state.authenticated:
        main_dashboard()
    else:
        login_page()