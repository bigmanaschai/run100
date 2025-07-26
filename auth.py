import sqlite3
import hashlib
import secrets
from datetime import datetime


def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


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


def get_user_role(user_id):
    """Get user role by ID"""
    conn = sqlite3.connect('runanalytics.db')
    cursor = conn.cursor()

    cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()

    conn.close()
    return result[0] if result else None


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


def update_user_password(user_id, new_password):
    """Update user password"""
    conn = sqlite3.connect('runanalytics.db')
    cursor = conn.cursor()

    hashed_password = hash_password(new_password)
    cursor.execute("""
                   UPDATE users
                   SET password = ?
                   WHERE id = ?
                   """, (hashed_password, user_id))

    conn.commit()
    conn.close()
    return True


def generate_session_token():
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)


def validate_session(token):
    """Validate session token"""
    # Implementation would depend on session storage method
    # For now, this is a placeholder
    return True