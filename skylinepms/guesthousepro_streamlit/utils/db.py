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

@contextmanager
def get_conn():
    """
    Context manager that yields a PostgreSQL connection using Streamlit secrets.
    Ensures commits are processed automatically and cleans up the connection.
    """
    try:
        # Load parameters explicitly to prevent username parsing confusion
        conn = psycopg2.connect(
            host=st.secrets["database"]["host"],
            port=int(st.secrets["database"]["port"]),
            database=st.secrets["database"]["database"],
            user=st.secrets["database"]["user"],
            password=st.secrets["database"]["password"],
            sslmode="require"
        )
        yield conn
        conn.commit()
    except Exception as e:
        raise e
    finally:
        if 'conn' in locals() and conn:
            conn.close()

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
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT * FROM accounts WHERE email = %s;", (email,))
                return cur.fetchone()
    except Exception:
        return None

def get_account_by_username(username: str):
    """Retrieves an account record matching the provided username/email identifier."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # Checks email field since your auth module uses username interchangeably
                cur.execute("SELECT * FROM accounts WHERE email = %s;", (username,))
                return cur.fetchone()
    except Exception:
        return None

def create_account(email: str, password_raw: str):
    """Registers a brand new manager account with a securely hashed password."""
    pwd_hash = hash_password(password_raw)
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    "INSERT INTO accounts (email, password_hash) VALUES (%s, %s) RETURNING *;",
                    (email, pwd_hash)
                )
                return cur.fetchone()
    except Exception:
        return None

# ---------- Schema & Tables Auto-Creation ----------

def init_db():
    """
    Creates tables inside your Supabase PostgreSQL cluster automatically if they don't exist.
    Preserves multi-account setups with 'account_id'.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
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

            # 4. Reservations / Bookings Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id SERIAL PRIMARY KEY,
                    account_id INTEGER NOT NULL,
                    guest_id INTEGER,
                    unit_number TEXT NOT NULL,
                    check_in TEXT NOT NULL,
                    check_out TEXT NOT NULL,
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
            # Checks if the database accounts table is completely empty
            cur.execute("SELECT COUNT(*) FROM accounts;")
            if cur.fetchone()[0] == 0:
                # Fetch your admin credentials safely from Streamlit TOML configurations
                admin_user = st.secrets["auth"]["username"]
                admin_pass = st.secrets["auth"]["password"]
                
                # Securely hash the password string using your custom token framework
                hashed_pass = hash_password(admin_pass)
                
                # Provision the initial master admin credentials row
                cur.execute(
                    "INSERT INTO accounts (email, password_hash) VALUES (%s, %s);",
                    (admin_user, hashed_pass)
                )

# Run the database setup script cleanly on app launch
try:
    init_db()
except Exception:
    pass
