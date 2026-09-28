"""
Database layer for user management and personalized STRATZ API tokens.
Uses SQLite (embedded, zero-configuration) stored in data/users.db.
"""

import os
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
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
            SELECT id, email, name, avatar_url, stratz_token, created_at 
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
        return res


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


# Ensure DB schema is ready on module import
init_db()
