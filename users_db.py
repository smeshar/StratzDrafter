"""
Database layer for user management and personalized STRATZ API tokens.
Uses SQLite (embedded, zero-configuration) stored in data/users.db.
"""

import os
import json
import sqlite3
from typing import Optional, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "users.db")


def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the database schema if not already present."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                name TEXT NOT NULL,
                password_hash TEXT,
                google_id TEXT UNIQUE,
                avatar_url TEXT,
                stratz_token TEXT,
                custom_weights TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS site_stats (
                key TEXT PRIMARY KEY,
                value INTEGER NOT NULL DEFAULT 0
            )
        """)
        # Ensure custom_weights and selected_bracket columns exist for existing DBs
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "custom_weights" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN custom_weights TEXT")
        if "selected_bracket" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN selected_bracket TEXT")
        conn.commit()


def register_user(email: str, password: str, name: Optional[str] = None) -> Dict[str, Any]:
    """Registers a new standard user with email and hashed password."""
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("Некорректный email адрес")
    if not password or len(password) < 4:
        raise ValueError("Пароль должен содержать минимум 4 символа")

    display_name = name.strip() if name and name.strip() else email.split("@")[0]
    p_hash = generate_password_hash(password)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            raise ValueError("Пользователь с таким email уже зарегистрирован")

        cursor.execute("""
            INSERT INTO users (email, name, password_hash)
            VALUES (?, ?, ?)
        """, (email, display_name, p_hash))
        conn.commit()
        user_id = cursor.lastrowid

        return get_user_by_id(user_id)


def authenticate_user(login_or_email: str, password: str) -> Optional[Dict[str, Any]]:
    """Verifies email or username and password; returns user dict or None."""
    identifier = login_or_email.strip().lower()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = ? OR LOWER(name) = ?", (identifier, identifier))
        row = cursor.fetchone()
        if not row:
            return None
        if not row["password_hash"] or not check_password_hash(row["password_hash"], password):
            return None

        return dict(row)


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves safe user profile dictionary (excluding password hash)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, name, avatar_url, stratz_token, custom_weights, selected_bracket, created_at 
            FROM users WHERE id = ?
        """, (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["hasStratzToken"] = bool(res.get("stratz_token"))
        # Mask the token for safety: show only last 4 chars if present
        token = res.get("stratz_token") or ""
        res["maskedToken"] = f"...{token[-4:]}" if len(token) >= 8 else ("*****" if token else "")
        # Parse custom default weights
        raw_weights = res.get("custom_weights")
        if raw_weights:
            try:
                res["customWeights"] = json.loads(raw_weights)
            except Exception:
                res["customWeights"] = {"counter": 100, "synergy": 50, "meta": 25}
        else:
            res["customWeights"] = {"counter": 100, "synergy": 50, "meta": 25}
        res["selectedBracket"] = res.get("selected_bracket") or "ARCHON"
        return res


def update_user_custom_weights(user_id: int, weights: Dict[str, Any]) -> bool:
    """Updates user's custom default weights for counter, synergy, and meta."""
    clean_weights = {
        "counter": max(0, min(100, int(weights.get("counter", 100)))),
        "synergy": max(0, min(100, int(weights.get("synergy", 50)))),
        "meta": max(0, min(100, int(weights.get("meta", 25)))),
    }
    with get_db_connection() as conn:
        conn.execute("UPDATE users SET custom_weights = ? WHERE id = ?", (json.dumps(clean_weights), user_id))
        conn.commit()
        return True


def update_user_bracket(user_id: int, bracket: str) -> bool:
    """Updates user's preferred rank bracket (HERALD, GUARDIAN, ARCHON, etc.)."""
    clean_bracket = bracket.strip().upper() if bracket else "ARCHON"
    with get_db_connection() as conn:
        conn.execute("UPDATE users SET selected_bracket = ? WHERE id = ?", (clean_bracket, user_id))
        conn.commit()
        return True


def update_user_stratz_token(user_id: int, token: Optional[str]) -> bool:
    """Updates user's personalized STRATZ API Bearer token."""
    clean_token = token.strip() if token else None
    with get_db_connection() as conn:
        conn.execute("UPDATE users SET stratz_token = ? WHERE id = ?", (clean_token, user_id))
        conn.commit()
        return True


def get_raw_stratz_token_for_user(user_id: int) -> Optional[str]:
    """Returns actual unmasked STRATZ API token for backend request forwarding."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT stratz_token FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return row["stratz_token"] if row and row["stratz_token"] else None


def increment_stat(key: str, amount: int = 1) -> int:
    """Increments integer statistic key atomically and returns new value."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM site_stats WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row is None:
            new_val = amount
            cursor.execute("INSERT INTO site_stats (key, value) VALUES (?, ?)", (key, new_val))
        else:
            new_val = row["value"] + amount
            cursor.execute("UPDATE site_stats SET value = ? WHERE key = ?", (new_val, key))
        conn.commit()
        return new_val


def get_stat(key: str, default: int = 0) -> int:
    """Retrieves integer statistic key."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM site_stats WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default


def set_stat(key: str, value: int):
    """Sets integer statistic key to a specific value."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM site_stats WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row is None:
            cursor.execute("INSERT INTO site_stats (key, value) VALUES (?, ?)", (key, value))
        else:
            cursor.execute("UPDATE site_stats SET value = ? WHERE key = ?", (value, key))
        conn.commit()


import time
import threading


class ViewerTracker:
    """Thread-safe in-memory tracker for active site viewers."""
    def __init__(self, timeout_seconds: int = 35):
        self.timeout_seconds = timeout_seconds
        self._lock = threading.Lock()
        self._viewers: Dict[str, float] = {}

    def record_activity(self, visitor_id: Optional[str] = None):
        if not visitor_id:
            visitor_id = "guest_default"
        now = time.time()
        with self._lock:
            self._viewers[str(visitor_id)] = now
            if len(self._viewers) > 150:
                cutoff = now - 300
                self._viewers = {k: v for k, v in self._viewers.items() if v >= cutoff}

    def get_online_count(self) -> int:
        now = time.time()
        cutoff = now - self.timeout_seconds
        with self._lock:
            count = sum(1 for ts in self._viewers.values() if ts >= cutoff)
            return max(1, count)


viewer_tracker = ViewerTracker()


# Ensure DB schema is ready on module import
init_db()
