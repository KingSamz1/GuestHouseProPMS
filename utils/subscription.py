"""
GuesthousePro subscription logic — PostgreSQL version.
"""
import calendar
import secrets
import string
import streamlit as st
from datetime import date, datetime, timedelta
from utils.db import get_conn
from utils.pg import fetchone, fetchall, execute, lastrowid, scalar
from utils.currency import MONTHLY_FEE_UGX

MONTHLY_FEE    = MONTHLY_FEE_UGX
GRACE_DAYS     = 2
ADMIN_USERNAME = "samzinov"


def _today():   return date.today()

def _ds(d):
    """Convert a date/datetime to a plain YYYY-MM-DD string."""
    if isinstance(d, datetime):
        return d.strftime("%Y-%m-%d")
    return d.isoformat()

def _parse(value):
    """
    Safely convert any date-like value to a plain date object.
    Handles: None, str, datetime.date, datetime.datetime.
    PostgreSQL TIMESTAMP columns return datetime objects — we strip the time part.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    # String fallback — take first 10 chars (YYYY-MM-DD)
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()

def _add_month(d, months=1):
    month_index = d.month - 1 + months
    year  = d.year + month_index // 12
    month = month_index % 12 + 1
    last  = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last))

def _make_code(length=10):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _sanitize(rows):
    """Convert any datetime objects in a list of dicts to ISO strings."""
    result = []
    for row in rows:
        row = dict(row)
        for k, v in row.items():
            if isinstance(v, datetime):
                row[k] = v.isoformat()
            elif isinstance(v, date):
                row[k] = v.isoformat()
        result.append(row)
    return result


def _sanitize_one(row):
    """Convert any datetime objects in a single dict to ISO strings."""
    if not row:
        return row
    row = dict(row)
    for k, v in row.items():
        if isinstance(v, datetime):
            row[k] = v.isoformat()
        elif isinstance(v, date):
            row[k] = v.isoformat()
    return row


@st.cache_data(ttl=300, show_spinner=False)
def is_admin(account_id):
    with get_conn() as conn:
        row = fetchone(conn, "SELECT username FROM accounts WHERE id=%s", (account_id,))
        return bool(row and row["username"].lower() == ADMIN_USERNAME.lower())


def create_subscription(account_id, property_name):
    start     = _today()
    trial_end = _add_month(start) - timedelta(days=1)
    now       = datetime.now().isoformat()
    with get_conn() as conn:
        return lastrowid(conn,
            "INSERT INTO subscription (account_id, property_name, trial_start, trial_end, "
            "monthly_fee, status, created_at, updated_at) "
            "VALUES (%s,%s,%s,%s,%s,'TRIAL',%s,%s) RETURNING id",
            (account_id, property_name, _ds(start), _ds(trial_end), MONTHLY_FEE, now, now),
        )


def get_subscription(account_id):
    with get_conn() as conn:
        return fetchone(conn,
            "SELECT * FROM subscription WHERE account_id=%s ORDER BY id DESC LIMIT 1",
            (account_id,),
        )


def _due_date(sub):
    if sub["status"] == "TRIAL":
        return _parse(sub["trial_end"]) + timedelta(days=1)
    if sub["status"] == "ACTIVE":
        return _parse(sub["next_payment_date"])
    return None


def update_subscription_status(account_id):
    sub = get_subscription(account_id)
    if not sub: return None
    today  = _today()
    status = sub["status"]
    past_due = False
    grace_days_left = 0
    if status in ("TRIAL", "ACTIVE"):
        due         = _due_date(sub)
        lockout_day = due + timedelta(days=GRACE_DAYS)
        if today >= lockout_day:
            status = "EXPIRED"
        elif today >= due:
            past_due = True
            grace_days_left = (lockout_day - today).days
    if status != sub["status"]:
        with get_conn() as conn:
            execute(conn,
                "UPDATE subscription SET status=%s, updated_at=%s WHERE id=%s",
                (status, datetime.now().isoformat(), sub["id"]),
            )
        sub = dict(sub)
        sub["status"] = status
    sub = dict(sub)
    sub["past_due"]        = past_due
    sub["grace_days_left"] = grace_days_left
    return sub


def days_remaining(account_id):
    sub = update_subscription_status(account_id)
    if not sub: return 0
    today = _today()
    if sub["status"] == "TRIAL":
        end_date = _parse(sub["trial_end"])
    elif sub["status"] == "ACTIVE":
        end_date = _parse(sub["next_payment_date"]) - timedelta(days=1)
    else:
        return 0
    return max(0, (end_date - today).days + 1)


def system_active(account_id):
    if is_admin(account_id): return True
    sub = update_subscription_status(account_id)
    if not sub: return False
    return sub["status"] in ("TRIAL", "ACTIVE")


def subscription_payment_history(account_id):
    with get_conn() as conn:
        sub = fetchone(conn,
            "SELECT id FROM subscription WHERE account_id=%s ORDER BY id DESC LIMIT 1",
            (account_id,),
        )
        if not sub: return []
        rows = fetchall(conn,
            "SELECT * FROM subscription_payments WHERE subscription_id=%s ORDER BY payment_date DESC",
            (sub["id"],),
        )
        return _sanitize(rows)


def generate_renewal_code(admin_account_id, months=1):
    if not is_admin(admin_account_id):
        raise PermissionError("Only the admin account can generate renewal codes.")
    for _ in range(10):
        code = _make_code()
        try:
            with get_conn() as conn:
                execute(conn,
                    "INSERT INTO renewal_codes (code, months, created_by) VALUES (%s,%s,%s)",
                    (code, months, admin_account_id),
                )
            return code
        except Exception:
            continue
    raise RuntimeError("Could not generate a unique code.")


def list_renewal_codes(admin_account_id):
    if not is_admin(admin_account_id):
        raise PermissionError("Only the admin account can view renewal codes.")
    with get_conn() as conn:
        rows = fetchall(conn,
            "SELECT rc.*, a.username AS used_by_username "
            "FROM renewal_codes rc "
            "LEFT JOIN accounts a ON a.id=rc.used_by "
            "ORDER BY rc.created_at DESC",
        )
        return _sanitize(rows)


def redeem_renewal_code(account_id, code):
    code = code.strip().upper()
    if not code: raise ValueError("Please enter a renewal code.")
    with get_conn() as conn:
        row = fetchone(conn, "SELECT * FROM renewal_codes WHERE code=%s", (code,))
        if not row:          raise ValueError("Invalid code — check with your administrator.")
        if row["used_by"]:   raise ValueError("This code has already been used.")
        sub     = get_subscription(account_id)
        if not sub:          raise ValueError("No subscription found for your account.")
        months  = row["months"]
        today   = _today()
        if sub["status"] == "TRIAL":
            period_start = _parse(sub["trial_end"]) + timedelta(days=1)
        elif sub["status"] == "ACTIVE":
            period_start = _parse(sub["next_payment_date"])
        else:
            period_start = today
        period_end   = _add_month(period_start, months) - timedelta(days=1)
        next_payment = _add_month(period_start, months)
        now = datetime.now().isoformat()
        execute(conn, "UPDATE renewal_codes SET used_by=%s, used_at=%s WHERE id=%s",
                (account_id, now, row["id"]))
        execute(conn,
            "INSERT INTO subscription_payments "
            "(subscription_id, amount, payment_date, payment_method, transaction_reference, "
            "period_start, period_end, note, created_at) VALUES (%s,%s,%s,'Code',%s,%s,%s,%s,%s)",
            (sub["id"], MONTHLY_FEE * months, _ds(today), code,
             _ds(period_start), _ds(period_end),
             f"Renewed via code — {months} month(s)", now),
        )
        execute(conn,
            "UPDATE subscription SET status='ACTIVE', subscription_start=%s, "
            "next_payment_date=%s, updated_at=%s WHERE id=%s",
            (_ds(period_start), _ds(next_payment), now, sub["id"]),
        )
    return _sanitize_one(get_subscription(account_id))


def fast_forward(account_id, days):
    sub = get_subscription(account_id)
    if not sub: raise ValueError("No subscription found.")
    with get_conn() as conn:
        if sub["status"] == "TRIAL":
            new_end = _parse(sub["trial_end"]) - timedelta(days=days)
            execute(conn, "UPDATE subscription SET trial_end=%s, updated_at=%s WHERE id=%s",
                    (_ds(new_end), datetime.now().isoformat(), sub["id"]))
        else:
            new_next = _parse(sub["next_payment_date"]) - timedelta(days=days)
            execute(conn, "UPDATE subscription SET next_payment_date=%s, updated_at=%s WHERE id=%s",
                    (_ds(new_next), datetime.now().isoformat(), sub["id"]))
    return update_subscription_status(account_id)


def force_expire(account_id):
    sub = get_subscription(account_id)
    if not sub: raise ValueError("No subscription found.")
    with get_conn() as conn:
        execute(conn, "UPDATE subscription SET status='EXPIRED', updated_at=%s WHERE id=%s",
                (datetime.now().isoformat(), sub["id"]))
    return get_subscription(account_id)


# ── Password reset codes ───────────────────────────────────────────────────────

def generate_password_reset_code(admin_account_id, target_account_id):
    if not is_admin(admin_account_id):
        raise PermissionError("Only the admin account can generate reset codes.")
    expires = (datetime.now() + timedelta(hours=24)).isoformat()
    for _ in range(10):
        code = _make_code(8)
        try:
            with get_conn() as conn:
                execute(conn,
                    "INSERT INTO password_reset_codes "
                    "(code, target_account_id, created_by, expires_at) VALUES (%s,%s,%s,%s)",
                    (code, target_account_id, admin_account_id, expires),
                )
            return code
        except Exception:
            continue
    raise RuntimeError("Could not generate a unique code.")


def list_password_reset_codes(admin_account_id):
    if not is_admin(admin_account_id):
        raise PermissionError("Only the admin account can view reset codes.")
    with get_conn() as conn:
        rows = fetchall(conn,
            "SELECT prc.*, a.username AS target_username "
            "FROM password_reset_codes prc "
            "JOIN accounts a ON a.id=prc.target_account_id "
            "ORDER BY prc.created_at DESC LIMIT 50",
        )
        return _sanitize(rows)


def verify_password_reset_code(username, code):
    code = code.strip().upper()
    if not code: raise ValueError("Please enter the reset code.")
    from utils.db import get_account_by_username
    account = get_account_by_username(username.strip())
    if not account: raise ValueError("Username not found.")
    with get_conn() as conn:
        row = fetchone(conn,
            "SELECT * FROM password_reset_codes WHERE code=%s AND target_account_id=%s",
            (code, account["id"]),
        )
        if not row:        raise ValueError("Invalid code for this username. Check with support.")
        if row["used_at"]: raise ValueError("This code has already been used.")
        expires_at = _parse(row["expires_at"])
        if expires_at and date.today() > expires_at + timedelta(days=1):
            raise ValueError("This code has expired. Ask support for a new one.")
    return account["id"]


def redeem_password_reset_code(username, code):
    acc_id = verify_password_reset_code(username, code)
    code = code.strip().upper()
    with get_conn() as conn:
        execute(conn,
            "UPDATE password_reset_codes SET used_at=%s WHERE code=%s",
            (datetime.now().isoformat(), code),
        )
    return acc_id
