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
        # Connect to Supabase via the TOML secret URL you saved
        conn = psycopg2.connect(st.secrets["database"]["url"])
        yield conn
        conn.commit()
    except Exception as e:
        st.error(f"Database transaction failure: {e}")
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

# Trigger table structure setup on initialization
try:
    init_db()
except Exception as schema_err:
    st.error(f"Failed to provision database layout: {schema_err}")
