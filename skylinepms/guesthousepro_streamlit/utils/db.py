"""
Database layer for GuesthousePro.
PostgreSQL (Supabase), cloud-hosted, created automatically on first run.

Multi-account: every major table carries account_id so each property
manager sees only their own data.

Core domain: units, guests, reservations/bookings, folios (billing),
payments, housekeeping, maintenance, expenses, booking sources.
"""
import streamlit as st
import psycopg2
from psycopg2.extras import DictCursor
import hashlib
import secrets
from datetime import datetime
from contextlib import contextmanager

# ---------- SQLite Compatibility Wrappers ----------

class SQLiteCompatCursor:
    """A compatibility cursor wrapper mimicking legacy SQLite row-fetching syntax."""
    def __init__(self, cur):
        self.cur = cur

    def execute(self, query, params=None):
        self.cur.execute(query, params)
        return self

    def fetchone(self):
        try:
            row = self.cur.fetchone()
            if row:
                row_dict = dict(row)
                if "email" in row_dict and "username" not in row_dict:
                    row_dict["username"] = row_dict["email"]
                return row_dict
        except Exception:
            pass
        return None

    def fetchall(self):
        try:
            rows = self.cur.fetchall()
            result = []
            for row in rows:
                row_dict = dict(row)
                if "email" in row_dict and "username" not in row_dict:
                    row_dict["username"] = row_dict["email"]
                result.append(row_dict)
            return result
        except Exception:
            return []

    def __getitem__(self, key):
        row = self.cur.fetchone()
        if row:
            row_dict = dict(row)
            if "email" in row_dict and "username" not in row_dict:
                row_dict["username"] = row_dict["email"]
            return row_dict[key]
        raise IndexError("No rows returned from query execution match.")


class SQLiteCompatConnection:
    """A connection wrapper mimicking SQLite API signatures on top of PostgreSQL."""
    def __init__(self, conn):
        self.conn = conn

    def execute(self, query, params=None):
        if not query:
            return None

        # Convert SQLite style '?' parameter placeholders to PostgreSQL '%s' tokens
        if "?" in query:
            query = query.replace("?", "%s")
            
        if "username" in query.lower():
            query = query.replace("username", "email")
            
        cur = self.conn.cursor(cursor_factory=DictCursor)
        compat_cursor = SQLiteCompatCursor(cur)
        compat_cursor.execute(query, params)
        return compat_cursor

    def cursor(self, *args, **kwargs):
        cur = self.conn.cursor(*args, **kwargs)
        return SQLiteCompatCursor(cur)

    def commit(self):
        return self.conn.commit()

    def rollback(self):
        return self.conn.rollback()

    def close(self):
        return self.conn.close()


@contextmanager
def get_conn():
    """
    Context manager that yields a PostgreSQL connection using Streamlit secrets.
    Wraps the connection to intercept and support legacy SQLite syntax seamlessly.
    """
    try:
        raw_conn = psycopg2.connect(
            host=st.secrets["database"]["host"],
            port=int(st.secrets["database"]["port"]),
            database=st.secrets["database"]["database"],
            user=st.secrets["database"]["user"],
            password=st.secrets["database"]["password"],
            sslmode="require"
        )
        yield SQLiteCompatConnection(raw_conn)
        raw_conn.commit()
    except Exception as e:
        raise e
    finally:
        if 'raw_conn' in locals() and raw_conn:
            raw_conn.close()


# ---------- Password helpers ----------

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split(":", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
    except Exception:
        return False


# ---------- Account Lookup Helpers ----------

def get_account(email: str):
    """Retrieves an account record matching the provided email address."""
    try:
        with get_conn() as conn:
            res = conn.execute("SELECT * FROM accounts WHERE email = %s;", (email,))
            return res.fetchone()
    except Exception:
        return None


def get_account_by_username(username: str):
    """Retrieves an account record matching the provided username/email identifier."""
    try:
        with get_conn() as conn:
            res = conn.execute("SELECT * FROM accounts WHERE email = %s;", (username,))
            return res.fetchone()
    except Exception:
        return None


def create_account(email: str, password_raw: str):
    """Registers a brand new manager account with a securely hashed password."""
    pwd_hash = hash_password(password_raw)
    try:
        with get_conn() as conn:
            res = conn.execute(
                "INSERT INTO accounts (email, password_hash) VALUES (%s, %s) RETURNING *;",
                (email, pwd_hash)
            )
            return res.fetchone()
    except Exception:
        return None


# ---------- Schema & Tables Auto-Creation ----------

def init_db():
    """
    Creates tables inside your Supabase PostgreSQL cluster automatically if they don't exist.
    Matches the exact column and table layout your frontend queries use.
    """
    with get_conn() as conn:
        with conn.conn.cursor() as cur:
            # 1. Accounts Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Units / Rooms Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS units (
                    id SERIAL PRIMARY KEY,
                    account_id INTEGER NOT NULL,
                    unit_number TEXT NOT NULL,
                    unit_type TEXT NOT NULL,
                    price_per_night REAL NOT NULL,
                    status TEXT DEFAULT 'Available',
                    UNIQUE(account_id, unit_number)
                );
            """)

            # 3. Guests Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS guests (
                    id SERIAL PRIMARY KEY,
                    account_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    id_number TEXT
                );
            """)

            # 4. Bookings / Reservations Table (Aligned completely to your frontend schema)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id SERIAL PRIMARY KEY,
                    account_id INTEGER NOT NULL,
                    guest_id INTEGER REFERENCES guests(id) ON DELETE SET NULL,
                    unit_id INTEGER REFERENCES units(id) ON DELETE SET NULL,
                    check_in_date TEXT NOT NULL,
                    check_out_date TEXT NOT NULL,
                    total_amount REAL NOT NULL,
                    amount_paid REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'Confirmed'
                );
            """)

            # 5. Expenses Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id SERIAL PRIMARY KEY,
                    account_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    date TEXT NOT NULL
                );
            """)
            
            # --- AUTO-SEED ADMIN USER ACCOUNT ---
            cur.execute("SELECT COUNT(*) FROM accounts;")
            count = cur.fetchone()
            
            if isinstance(count, (list, tuple)):
                count_val = count[0]
            elif isinstance(count, dict):
                count_val = list(count.values())[0]
            else:
                count_val = count

            if count_val == 0:
                admin_user = st.secrets["auth"]["username"]
                admin_pass = st.secrets["auth"]["password"]
                hashed_pass = hash_password(admin_pass)
                cur.execute(
                    "INSERT INTO accounts (email, password_hash) VALUES (%s, %s);",
                    (admin_user, hashed_pass)
                )

try:
    init_db()
except Exception:
    pass
