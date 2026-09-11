"""
Database layer for SkylinePMS.
SQLite, single-file, created automatically on first run.

Multi-account: every major table carries account_id so each property
manager sees only their own data.

Core domain: units, guests, reservations/bookings, folios (billing),
payments, housekeeping, maintenance, expenses, booking sources.
"""
import sqlite3
import os
import hashlib
import secrets
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "skyline.db"
)


def _ensure_data_dir():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@contextmanager
def get_conn():
    _ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
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


# ---------- Schema ----------

def init_db():
    """Create all tables if they don't exist. Safe to call every run."""
    with get_conn() as conn:
        c = conn.cursor()

        # Accounts — one row per property manager
        c.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL DEFAULT '',
            property_name TEXT NOT NULL DEFAULT 'My Property',
            currency TEXT NOT NULL DEFAULT 'UGX',
            business_phone TEXT NOT NULL DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # Units / Apartments (the 14 rooms)
        c.execute("""
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """)

        # Guest profiles
        c.execute("""
        CREATE TABLE IF NOT EXISTS guests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """)

        # Reservations / bookings
        c.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
            FOREIGN KEY (guest_id) REFERENCES guests(id) ON DELETE RESTRICT
        )
        """)

        # Folio items — extra charges added to a booking
        c.execute("""
        CREATE TABLE IF NOT EXISTS folio_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE
        )
        """)

        # Payments against a reservation
        c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            method TEXT NOT NULL DEFAULT 'cash',
            momo_reference TEXT NOT NULL DEFAULT '',
            momo_provider TEXT NOT NULL DEFAULT '',
            payment_type TEXT NOT NULL DEFAULT 'accommodation',
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE
        )
        """)

        # Receipts
        c.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id INTEGER NOT NULL,
            receipt_number TEXT NOT NULL UNIQUE,
            file_path TEXT NOT NULL,
            download_name TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE CASCADE
        )
        """)

        # Housekeeping tasks
        c.execute("""
        CREATE TABLE IF NOT EXISTS housekeeping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL DEFAULT 1,
            unit_id INTEGER NOT NULL,
            task_type TEXT NOT NULL DEFAULT 'clean',
            status TEXT NOT NULL DEFAULT 'pending',
            assigned_to TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE
        )
        """)

        # Maintenance issues
        c.execute("""
        CREATE TABLE IF NOT EXISTS maintenance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL DEFAULT 1,
            unit_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'medium',
            status TEXT NOT NULL DEFAULT 'open',
            assigned_to TEXT NOT NULL DEFAULT '',
            cost REAL NOT NULL DEFAULT 0,
            notes TEXT NOT NULL DEFAULT '',
            reported_at TEXT DEFAULT (datetime('now')),
            resolved_at TEXT,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE
        )
        """)

        # Expenses / operating costs
        c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL DEFAULT 1,
            category TEXT NOT NULL DEFAULT 'other',
            description TEXT NOT NULL DEFAULT '',
            amount REAL NOT NULL DEFAULT 0,
            expense_date TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """)

        # WhatsApp message log
        c.execute("""
        CREATE TABLE IF NOT EXISTS messages_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_id INTEGER NOT NULL,
            message_type TEXT NOT NULL DEFAULT 'confirmation',
            message TEXT NOT NULL,
            channel TEXT NOT NULL DEFAULT 'whatsapp',
            status TEXT NOT NULL DEFAULT 'prepared',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE
        )
        """)

        # Subscription
        c.execute("""
        CREATE TABLE IF NOT EXISTS subscription (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL DEFAULT 1,
            property_name TEXT NOT NULL,
            trial_start TEXT,
            trial_end TEXT,
            subscription_start TEXT,
            next_payment_date TEXT,
            monthly_fee REAL NOT NULL DEFAULT 100000,
            status TEXT NOT NULL DEFAULT 'TRIAL',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS subscription_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            payment_method TEXT,
            transaction_reference TEXT UNIQUE,
            period_start TEXT,
            period_end TEXT,
            note TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (subscription_id) REFERENCES subscription(id) ON DELETE CASCADE
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS renewal_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            months INTEGER NOT NULL DEFAULT 1,
            created_by INTEGER NOT NULL,
            used_by INTEGER,
            used_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        conn.commit()
        _migrate(c, conn)
        conn.commit()


def _col_exists(c, table, col):
    cols = [r["name"] for r in c.execute(f"PRAGMA table_info({table})").fetchall()]
    return col in cols


def _migrate(c, conn):
    """Non-destructive upgrades."""
    # Seed admin account
    existing_accounts = c.execute("SELECT COUNT(*) cnt FROM accounts").fetchone()["cnt"]
    if existing_accounts == 0:
        import streamlit as st
        try:
            username = st.secrets["auth"]["username"]
            raw_password = st.secrets["auth"]["password"]
            property_name = st.secrets.get("property", {}).get("property_name", "My Property")
            currency = st.secrets.get("property", {}).get("currency", "UGX")
            phone = st.secrets.get("property", {}).get("phone", "")
        except Exception:
            username = "admin"
            raw_password = "changeme123"
            property_name = "My Property"
            currency = "UGX"
            phone = ""
        pw_hash = hash_password(raw_password)
        c.execute(
            "INSERT OR IGNORE INTO accounts (id, username, password_hash, property_name, currency, business_phone) VALUES (1, ?, ?, ?, ?, ?)",
            (username, pw_hash, property_name, currency, phone),
        )

    ADMIN_USERNAME = "samzinov"
    ADMIN_PASSWORD = "s@mz!n0v"
    existing_admin = c.execute("SELECT id FROM accounts WHERE username = ? COLLATE NOCASE", (ADMIN_USERNAME,)).fetchone()
    if not existing_admin:
        admin_hash = hash_password(ADMIN_PASSWORD)
        c.execute(
            "INSERT OR IGNORE INTO accounts (username, password_hash, property_name, currency, business_phone) VALUES (?, ?, 'SkylinePMS Admin', 'UGX', '')",
            (ADMIN_USERNAME, admin_hash),
        )
    else:
        admin_hash = hash_password(ADMIN_PASSWORD)
        c.execute("UPDATE accounts SET password_hash = ? WHERE username = ? COLLATE NOCASE", (admin_hash, ADMIN_USERNAME))


# ---------- Account helpers ----------

def get_account(account_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        return dict(row) if row else None


def get_account_by_username(username):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM accounts WHERE username = ? COLLATE NOCASE", (username,)).fetchone()
        return dict(row) if row else None


def create_account(username, password, property_name="My Property", currency="UGX", business_phone=""):
    pw_hash = hash_password(password)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO accounts (username, password_hash, property_name, currency, business_phone) VALUES (?,?,?,?,?)",
            (username.strip(), pw_hash, property_name.strip(), currency.strip().upper(), business_phone.strip()),
        )
        return cur.lastrowid


def update_account_settings(account_id, property_name, currency, business_phone):
    with get_conn() as conn:
        conn.execute(
            "UPDATE accounts SET property_name=?, currency=?, business_phone=? WHERE id=?",
            (property_name, currency, business_phone, account_id),
        )


def update_account_password(account_id, new_password):
    with get_conn() as conn:
        conn.execute("UPDATE accounts SET password_hash=? WHERE id=?", (hash_password(new_password), account_id))


def list_all_accounts():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, username, property_name, currency, business_phone, created_at FROM accounts ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]


def delete_account(account_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
