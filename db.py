"""
Database layer for Multi-Agent AI Research Assistant
Uses SQLite for simplicity - no external DB server needed.
"""
import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'research_assistant.db')


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, is_admin INTEGER DEFAULT 0, created_at TEXT NOT NULL)")

    existing_cols = [row[1] for row in cur.execute("PRAGMA table_info(users)").fetchall()]
    if 'is_admin' not in existing_cols:
        cur.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")

    cur.execute("CREATE TABLE IF NOT EXISTS research_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, topic TEXT NOT NULL, status TEXT DEFAULT 'pending', created_at TEXT NOT NULL, FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE)")

    cur.execute("CREATE TABLE IF NOT EXISTS sources (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, title TEXT, url TEXT, raw_content TEXT, source_type TEXT, retrieved_at TEXT NOT NULL, FOREIGN KEY (session_id) REFERENCES research_sessions (id) ON DELETE CASCADE)")

    cur.execute("CREATE TABLE IF NOT EXISTS summaries (id INTEGER PRIMARY KEY AUTOINCREMENT, source_id INTEGER NOT NULL, summary_text TEXT, created_at TEXT NOT NULL, FOREIGN KEY (source_id) REFERENCES sources (id) ON DELETE CASCADE)")

    cur.execute("CREATE TABLE IF NOT EXISTS comparisons (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, comparison_text TEXT, key_similarities TEXT, key_differences TEXT, created_at TEXT NOT NULL, FOREIGN KEY (session_id) REFERENCES research_sessions (id) ON DELETE CASCADE)")

    cur.execute("CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, title TEXT, content TEXT, citations TEXT, created_at TEXT NOT NULL, FOREIGN KEY (session_id) REFERENCES research_sessions (id) ON DELETE CASCADE)")

    conn.commit()
    conn.close()


def create_user(username, email, password):
    conn = get_connection()
    try:
        existing_count = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()['c']
        is_admin = 1 if existing_count == 0 else 0
        conn.execute("INSERT INTO users (username, email, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?, ?)", (username, email, generate_password_hash(password), is_admin, datetime.utcnow().isoformat()))
        conn.commit()
        if is_admin:
            return True, "Account created successfully! As the first user, you are the Admin."
        return True, "Account created successfully"
    except sqlite3.IntegrityError:
        return False, "Username or email already exists"
    finally:
        conn.close()


def promote_to_admin(username):
    conn = get_connection()
    cur = conn.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (username,))
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated


def demote_from_admin(username):
    conn = get_connection()
    cur = conn.execute("UPDATE users SET is_admin = 0 WHERE username = ?", (username,))
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated


def verify_user(username, password):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if row and check_password_hash(row['password_hash'], password):
        return dict(row)
    return None


def get_user_by_id(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_session(user_id, topic):
    conn = get_connection()
    cur = conn.execute("INSERT INTO research_sessions (user_id, topic, status, created_at) VALUES (?, ?, ?, ?)", (user_id, topic, 'pending', datetime.utcnow().isoformat()))
    conn.commit()
    session_id = cur.lastrowid
    conn.close()
    return session_id


def update_session_status(session_id, status):
    conn = get_connection()
    conn.execute("UPDATE research_sessions SET status = ? WHERE id = ?", (status, session_id))
    conn.commit()
    conn.close()


def get_user_sessions(user_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM research_sessions WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session(session_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM research_sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_source(session_id, title, url, raw_content, source_type='web'):
    conn = get_connection()
    cur = conn.execute("INSERT INTO sources (session_id, title, url, raw_content, source_type, retrieved_at) VALUES (?, ?, ?, ?, ?, ?)", (session_id, title, url, raw_content, source_type, datetime.utcnow().isoformat()))
    conn.commit()
    source_id = cur.lastrowid
    conn.close()
    return source_id


def get_sources_for_session(session_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM sources WHERE session_id = ?", (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_summary(source_id, summary_text):
    conn = get_connection()
    conn.execute("INSERT INTO summaries (source_id, summary_text, created_at) VALUES (?, ?, ?)", (source_id, summary_text, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def get_summaries_for_session(session_id):
    conn = get_connection()
    rows = conn.execute("SELECT s.id as source_id, s.title, s.url, sm.summary_text FROM sources s JOIN summaries sm ON s.id = sm.source_id WHERE s.session_id = ?", (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_comparison(session_id, comparison_text, similarities, differences):
    conn = get_connection()
    conn.execute("INSERT INTO comparisons (session_id, comparison_text, key_similarities, key_differences, created_at) VALUES (?, ?, ?, ?, ?)", (session_id, comparison_text, similarities, differences, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def get_comparison_for_session(session_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM comparisons WHERE session_id = ? ORDER BY id DESC LIMIT 1", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_report(session_id, title, content, citations):
    conn = get_connection()
    cur = conn.execute("INSERT INTO reports (session_id, title, content, citations, created_at) VALUES (?, ?, ?, ?, ?)", (session_id, title, content, citations, datetime.utcnow().isoformat()))
    conn.commit()
    report_id = cur.lastrowid
    conn.close()
    return report_id


def get_report_for_session(session_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM reports WHERE session_id = ? ORDER BY id DESC LIMIT 1", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_users():
    conn = get_connection()
    rows = conn.execute("SELECT u.id, u.username, u.email, u.is_admin, u.created_at, COUNT(rs.id) as session_count FROM users u LEFT JOIN research_sessions rs ON rs.user_id = u.id GROUP BY u.id ORDER BY u.created_at ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_sessions_admin():
    conn = get_connection()
    rows = conn.execute("SELECT rs.*, u.username FROM research_sessions rs JOIN users u ON rs.user_id = u.id ORDER BY rs.created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_sessions_for_specific_user(user_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM research_sessions WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_platform_stats():
    conn = get_connection()
    total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()['c']
    total_sessions = conn.execute("SELECT COUNT(*) as c FROM research_sessions").fetchone()['c']
    total_reports = conn.execute("SELECT COUNT(*) as c FROM reports").fetchone()['c']
    total_sources = conn.execute("SELECT COUNT(*) as c FROM sources").fetchone()['c']
    completed = conn.execute("SELECT COUNT(*) as c FROM research_sessions WHERE status = 'completed'").fetchone()['c']
    conn.close()
    return {'total_users': total_users, 'total_sessions': total_sessions, 'total_reports': total_reports, 'total_sources': total_sources, 'completed': completed, 'pending': total_sessions - completed}


def get_dashboard_stats(user_id):
    conn = get_connection()
    total_sessions = conn.execute("SELECT COUNT(*) as c FROM research_sessions WHERE user_id = ?", (user_id,)).fetchone()['c']
    completed = conn.execute("SELECT COUNT(*) as c FROM research_sessions WHERE user_id = ? AND status = 'completed'", (user_id,)).fetchone()['c']
    total_reports = conn.execute("SELECT COUNT(*) as c FROM reports r JOIN research_sessions rs ON r.session_id = rs.id WHERE rs.user_id = ?", (user_id,)).fetchone()['c']
    total_sources = conn.execute("SELECT COUNT(*) as c FROM sources s JOIN research_sessions rs ON s.session_id = rs.id WHERE rs.user_id = ?", (user_id,)).fetchone()['c']
    conn.close()
    return {'total_sessions': total_sessions, 'completed': completed, 'pending': total_sessions - completed, 'total_reports': total_reports, 'total_sources': total_sources}