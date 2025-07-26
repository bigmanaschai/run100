import sqlite3
import json
from datetime import datetime
import pandas as pd


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

    # Video metadata table
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS video_metadata
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
                       file_name
                       TEXT,
                       file_size
                       INTEGER,
                       duration
                       REAL,
                       fps
                       INTEGER,
                       resolution
                       TEXT,
                       upload_date
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
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
        from auth import hash_password
        cursor.execute("""
                       INSERT INTO users (username, password, email, role)
                       VALUES (?, ?, ?, ?)
                       """, ('admin', hash_password('admin123'), 'admin@runanalytics.com', 'admin'))

    conn.commit()
    conn.close()


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


def get_range_performance(performance_id):
    """Get range-specific performance data"""
    conn = sqlite3.connect('runanalytics.db')
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT range_number,
                          range_name,
                          max_speed,
                          avg_speed,
                          time_taken,
                          distance
                   FROM range_performance
                   WHERE performance_id = ?
                   ORDER BY range_number
                   """, (performance_id,))

    ranges = []
    for row in cursor.fetchall():
        ranges.append({
            'range_number': row[0],
            'range_name': row[1],
            'max_speed': row[2],
            'avg_speed': row[3],
            'time_taken': row[4],
            'distance': row[5]
        })

    conn.close()
    return ranges


def get_runner_statistics(runner_id):
    """Get overall statistics for a runner"""
    conn = sqlite3.connect('runanalytics.db')
    cursor = conn.cursor()

    # Get overall stats
    cursor.execute("""
                   SELECT COUNT(*)          as total_sessions,
                          MAX(max_velocity) as best_max_velocity,
                          AVG(avg_velocity) as average_velocity,
                          MIN(total_time)   as best_time,
                          AVG(total_time)   as average_time
                   FROM performance_data
                   WHERE runner_id = ?
                   """, (runner_id,))

    stats = cursor.fetchone()

    # Get trend data
    cursor.execute("""
                   SELECT session_date,
                          max_velocity,
                          avg_velocity,
                          total_time
                   FROM performance_data
                   WHERE runner_id = ?
                   ORDER BY session_date DESC LIMIT 20
                   """, (runner_id,))

    trend_data = []
    for row in cursor.fetchall():
        trend_data.append({
            'date': row[0],
            'max_velocity': row[1],
            'avg_velocity': row[2],
            'total_time': row[3]
        })

    conn.close()

    return {
        'total_sessions': stats[0] or 0,
        'best_max_velocity': stats[1] or 0,
        'average_velocity': stats[2] or 0,
        'best_time': stats[3] or 0,
        'average_time': stats[4] or 0,
        'trend_data': trend_data
    }


def export_performance_data(runner_id, start_date=None, end_date=None):
    """Export performance data for reporting"""
    conn = sqlite3.connect('runanalytics.db')

    query = """
            SELECT p.session_date, \
                   p.max_velocity, \
                   p.avg_velocity, \
                   p.total_distance, \
                   p.total_time, \
                   r.range_name, \
                   r.max_speed, \
                   r.avg_speed, \
                   r.time_taken
            FROM performance_data p
                     JOIN range_performance r ON p.id = r.performance_id
            WHERE p.runner_id = ? \
            """

    params = [runner_id]

    if start_date:
        query += " AND p.session_date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND p.session_date <= ?"
        params.append(end_date)

    query += " ORDER BY p.session_date DESC, r.range_number"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    return df


def save_video_metadata(performance_id, range_number, metadata):
    """Save video metadata"""
    conn = sqlite3.connect('runanalytics.db')
    cursor = conn.cursor()

    cursor.execute("""
                   INSERT INTO video_metadata (performance_id, range_number, file_name,
                                               file_size, duration, fps, resolution)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   """, (
                       performance_id,
                       range_number,
                       metadata.get('file_name', ''),
                       metadata.get('file_size', 0),
                       metadata.get('duration', 0),
                       metadata.get('fps', 0),
                       metadata.get('resolution', '')
                   ))

    conn.commit()
    conn.close()