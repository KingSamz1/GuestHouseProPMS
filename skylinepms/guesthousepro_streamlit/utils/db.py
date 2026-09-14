"""
Database layer for GuesthousePro.
PostgreSQL via Supabase — persistent, survives every redeploy.

Uses a cached connection pool (psycopg2 + st.cache_resource) so each
user session reuses a persistent connection instead of opening a new one
on every button click — this is the main speed fix.
"""
import hashlib
import secrets
import streamlit as st
import psycopg2
import psycopg2.extras
import psycopg2.pool
from contextlib import contextmanager
from datetime import datetime, date


@st.cache_resource
def _get_pool():
    db = st.secrets["database"]
    return psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        host=db["host"],
        port=int(db["port"]),
        database=db["database"],
        user=db["user"],
        password=db["password"],
        sslmode="require",
    )


@contextmanager
def get_conn():
    pool = _get_pool()
    conn = pool.getconn()
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


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


def init_db():
    with get_conn() as conn:
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL DEFAULT '',
            property_name TEXT NOT NULL DEFAULT 'My Property',
            currency TEXT NOT NULL DEFAULT 'UGX',
            business_phone TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS units (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL DEFAULT 1,
            unit_number TEXT NOT NULL,
            unit_type TEXT NOT NULL DEFAULT 'standard',
            floor INTEGER NOT NULL DEFAULT 1,
            max_guests INTEGER NOT NULL DEFAULT 2,
            rate_nightly REAL NOT NULL DEFAULT 0,
            rate_weekend REAL NOT NULL DEFAULT 0,
            rate_monthly REAL NOT NULL DEFAULT 0,
            amenities TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'available',
            maintenance_status TEXT NOT NULL DEFAULT 'ok',
            notes TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS guests (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL DEFAULT 1,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            nationality TEXT NOT NULL DEFAULT '',
            id_number TEXT NOT NULL DEFAULT '',
            id_document_path TEXT NOT NULL DEFAULT '',
            company TEXT NOT NULL DEFAULT '',
            special_requests TEXT NOT NULL DEFAULT '',
            total_stays INTEGER NOT NULL DEFAULT 0,
            total_spent REAL NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL DEFAULT 1,
            booking_ref TEXT NOT NULL UNIQUE,
            unit_id INTEGER NOT NULL,
            guest_id INTEGER NOT NULL,
            check_in_date TEXT NOT NULL,
            check_out_date TEXT NOT NULL,
            num_guests INTEGER NOT NULL DEFAULT 1,
            rate_type TEXT NOT NULL DEFAULT 'nightly',
            rate_per_night REAL NOT NULL DEFAULT 0,
            num_nights INTEGER NOT NULL DEFAULT 1,
            accommodation_total REAL NOT NULL DEFAULT 0,
            deposit_paid REAL NOT NULL DEFAULT 0,
            booking_source TEXT NOT NULL DEFAULT 'direct',
            status TEXT NOT NULL DEFAULT 'reserved',
            special_requests TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
            FOREIGN KEY (guest_id) REFERENCES guests(id) ON DELETE RESTRICT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS folio_items (
            id SERIAL PRIMARY KEY,
            reservation_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            reservation_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            method TEXT NOT NULL DEFAULT 'cash',
            momo_reference TEXT NOT NULL DEFAULT '',
            momo_provider TEXT NOT NULL DEFAULT '',
            payment_type TEXT NOT NULL DEFAULT 'accommodation',
            note TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id SERIAL PRIMARY KEY,
            payment_id INTEGER NOT NULL,
            receipt_number TEXT NOT NULL UNIQUE,
            file_path TEXT NOT NULL,
            download_name TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS housekeeping (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL DEFAULT 1,
            unit_id INTEGER NOT NULL,
            task_type TEXT NOT NULL DEFAULT 'clean',
            status TEXT NOT NULL DEFAULT 'pending',
            assigned_to TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS maintenance (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL DEFAULT 1,
            unit_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'medium',
            status TEXT NOT NULL DEFAULT 'open',
            assigned_to TEXT NOT NULL DEFAULT '',
            cost REAL NOT NULL DEFAULT 0,
            notes TEXT NOT NULL DEFAULT '',
            reported_at TIMESTAMP DEFAULT NOW(),
            resolved_at TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL DEFAULT 1,
            category TEXT NOT NULL DEFAULT 'other',
            description TEXT NOT NULL DEFAULT '',
            amount REAL NOT NULL DEFAULT 0,
            expense_date TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS messages_log (
            id SERIAL PRIMARY KEY,
            reservation_id INTEGER NOT NULL,
            message_type TEXT NOT NULL DEFAULT 'confirmation',
            message TEXT NOT NULL,
            channel TEXT NOT NULL DEFAULT 'whatsapp',
            status TEXT NOT NULL DEFAULT 'prepared',
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS subscription (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL DEFAULT 1,
            property_name TEXT NOT NULL,
            trial_start TEXT,
            trial_end TEXT,
            subscription_start TEXT,
            next_payment_date TEXT,
            monthly_fee REAL NOT NULL DEFAULT 30000,
            status TEXT NOT NULL DEFAULT 'TRIAL',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS subscription_payments (
            id SERIAL PRIMARY KEY,
            subscription_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            payment_method TEXT,
            transaction_reference TEXT UNIQUE,
            period_start TEXT,
            period_end TEXT,
            note TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (subscription_id) REFERENCES subscription(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS renewal_codes (
            id SERIAL PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            months INTEGER NOT NULL DEFAULT 1,
            created_by INTEGER NOT NULL,
            used_by INTEGER,
            used_at TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_codes (
            id SERIAL PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            target_account_id INTEGER NOT NULL,
            created_by INTEGER NOT NULL,
            used_at TEXT,
            expires_at TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (target_account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """)

        conn.commit()
        _seed_admin(c, conn)
        conn.commit()


def _seed_admin(c, conn):
    c.execute("SELECT COUNT(*) FROM accounts")
    row   = c.fetchone()
    count = list(dict(row).values())[0] if row else 0

    if count == 0:
        try:
            username     = st.secrets["auth"]["username"]
            raw_password = st.secrets["auth"]["password"]
            prop_name    = st.secrets.get("property", {}).get("property_name", "My Property")
            currency     = st.secrets.get("property", {}).get("currency", "UGX")
            phone        = st.secrets.get("property", {}).get("phone", "")
        except Exception:
            username = "admin"; raw_password = "changeme123"
            prop_name = "My Property"; currency = "UGX"; phone = ""
        pw_hash = hash_password(raw_password)
        c.execute(
            "INSERT INTO accounts (username, password_hash, property_name, currency, business_phone) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (username) DO NOTHING",
            (username, pw_hash, prop_name, currency, phone),
        )

    ADMIN_USERNAME = "samzinov"
    ADMIN_PASSWORD = "s@mz!n0v"
    admin_hash = hash_password(ADMIN_PASSWORD)
    c.execute(
        "INSERT INTO accounts (username, password_hash, property_name, currency, business_phone) "
        "VALUES (%s, %s, 'GuesthousePro Admin', 'UGX', '') "
        "ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash",
        (ADMIN_USERNAME, admin_hash),
    )


@st.cache_data(ttl=60, show_spinner=False)
def get_account(account_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM accounts WHERE id = %s", (account_id,))
        row = c.fetchone()
        return dict(row) if row else None


def get_account_by_username(username):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM accounts WHERE LOWER(username) = LOWER(%s)", (username,))
        row = c.fetchone()
        return dict(row) if row else None


def create_account(username, password, property_name="My Property", currency="UGX", business_phone=""):
    pw_hash = hash_password(password)
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO accounts (username, password_hash, property_name, currency, business_phone) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (username.strip(), pw_hash, property_name.strip(), currency.strip().upper(), business_phone.strip()),
        )
        row = c.fetchone()
        return dict(row)["id"] if row else None


def update_account_settings(account_id, property_name, currency, business_phone):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE accounts SET property_name=%s, currency=%s, business_phone=%s WHERE id=%s",
            (property_name, currency, business_phone, account_id),
        )


def update_account_password(account_id, new_password):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE accounts SET password_hash=%s WHERE id=%s",
            (hash_password(new_password), account_id),
        )


def list_all_accounts():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, username, property_name, currency, business_phone, created_at "
            "FROM accounts ORDER BY id"
        )
        return [dict(r) for r in c.fetchall()]


def delete_account(account_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM accounts WHERE id = %s", (account_id,))
