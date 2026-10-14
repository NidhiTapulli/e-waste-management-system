import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager

# Default database file in the backend directory
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ewaste.db")


def get_db_path() -> str:
    """Returns the active database file path (supports test overrides via env var)."""
    return os.environ.get("EWASTE_DB_PATH", DEFAULT_DB_PATH)


@contextmanager
def get_db():
    """
    Context manager for SQLite database connections.
    Uses sqlite3.Row for dict-like access and ensures connections are cleanly closed.
    """
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with a random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
    )
    return f"{salt}:{key.hex()}"


def verify_password(stored_hash: str, provided_password: str) -> bool:
    """Verifies a plain password against the stored salt:hash string."""
    try:
        salt, key_hex = stored_hash.split(":", 1)
        key = hashlib.pbkdf2_hmac(
            "sha256", provided_password.encode("utf-8"), salt.encode("utf-8"), 100000
        )
        return hmac.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    """Initializes tables and seeds default admin and demo user accounts."""
    with get_db() as conn:
        # Collection requests table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS collection_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_id TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                city TEXT NOT NULL,
                pincode TEXT NOT NULL,
                category TEXT NOT NULL,
                item_description TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                condition TEXT NOT NULL,
                preferred_date TEXT NOT NULL,
                special_notes TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_status ON collection_requests(status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_category ON collection_requests(category);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_created ON collection_requests(created_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_email ON collection_requests(email);")

        # Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL
            );
        """)

        # Active user sessions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # Seed predefined admin if not already existing
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@ewaste.com").strip().lower()
        admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO users (email, password_hash, full_name, role, created_at)
                VALUES (?, ?, ?, 'admin', ?)
                """,
                (
                    admin_email,
                    hash_password(admin_password),
                    "System Administrator",
                    _now_iso(),
                ),
            )

        # Seed predefined demo user if not already existing
        user_email = os.environ.get("DEMO_USER_EMAIL", "user@ewaste.com").strip().lower()
        user_password = os.environ.get("DEMO_USER_PASSWORD", "user123")
        cursor.execute("SELECT id FROM users WHERE email = ?", (user_email,))
        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO users (email, password_hash, full_name, role, created_at)
                VALUES (?, ?, ?, 'user', ?)
                """,
                (
                    user_email,
                    hash_password(user_password),
                    "Demo Resident User",
                    _now_iso(),
                ),
            )
