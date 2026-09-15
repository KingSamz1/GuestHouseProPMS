"""
Business logic for GuesthousePro — PostgreSQL version.
All queries use %s placeholders and the pg helper functions.
"""
import os
import secrets
from datetime import date, datetime
from utils.db import get_conn
from utils.pg import fetchall, fetchone, execute, lastrowid, scalar

def _san(rows):
    """Convert datetime objects in query results to ISO strings."""
    from datetime import datetime, date as _date
    out = []
    for row in rows:
        row = dict(row)
        for k, v in row.items():
            if isinstance(v, (datetime, _date)):
                row[k] = v.isoformat()
        out.append(row)
    return out


def _san1(row):
    from datetime import datetime, date as _date
    if not row: return row
    row = dict(row)
    for k, v in row.items():
        if isinstance(v, (datetime, _date)):
            row[k] = v.isoformat()
    return row


GUEST_DOCS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "guest_documents"
)

UNIT_TYPES    = ["2 Bedroom", "1 Bedroom", "Bachelor Studio", "Suite", "Standard", "Other"]
UNIT_STATUSES = ["available", "occupied", "reserved", "cleaning", "maintenance", "dirty", "inspected"]
BOOKING_SOURCES = [
    "Direct WhatsApp", "Phone Call", "Walk-in", "Website", "Facebook",
    "Instagram", "Airbnb", "Booking.com", "Referral", "Corporate",
    "Travel Agent", "Other",
]
PAYMENT_METHODS  = ["cash", "mobile_money", "bank", "card", "other"]
EXPENSE_CATEGORIES = [
    "Electricity", "Water", "Internet/WiFi", "Cleaning Supplies",
    "Maintenance", "Staff", "Laundry", "Marketing", "Other",
]


def _make_ref():
    year = datetime.now().strftime("%Y")
    rand = secrets.token_hex(3).upper()
    return f"GHP-{year}-{rand}"


# ── Units ──────────────────────────────────────────────────────────────────────

def add_unit(account_id, unit_number, unit_type, floor, max_guests,
             rate_nightly, rate_weekend, rate_monthly, amenities="", notes=""):
    with get_conn() as conn:
        return lastrowid(conn,
            "INSERT INTO units (account_id, unit_number, unit_type, floor, max_guests, "
            "rate_nightly, rate_weekend, rate_monthly, amenities, notes) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (account_id, unit_number, unit_type, floor, max_guests,
             rate_nightly, rate_weekend, rate_monthly, amenities, notes),
        )


def list_units(account_id=1):
    with get_conn() as conn:
        return fetchall(conn,
            "SELECT * FROM units WHERE account_id = %s ORDER BY unit_number",
            (account_id,),
        )


def get_unit(unit_id):
    with get_conn() as conn:
        return fetchone(conn, "SELECT * FROM units WHERE id = %s", (unit_id,))


def update_unit(unit_id, unit_number, unit_type, floor, max_guests,
                rate_nightly, rate_weekend, rate_monthly, amenities="", notes=""):
    with get_conn() as conn:
        execute(conn,
            "UPDATE units SET unit_number=%s, unit_type=%s, floor=%s, max_guests=%s, "
            "rate_nightly=%s, rate_weekend=%s, rate_monthly=%s, amenities=%s, notes=%s "
            "WHERE id=%s",
            (unit_number, unit_type, floor, max_guests,
             rate_nightly, rate_weekend, rate_monthly, amenities, notes, unit_id),
        )


def update_unit_status(unit_id, status):
    with get_conn() as conn:
        execute(conn, "UPDATE units SET status=%s WHERE id=%s", (status, unit_id))


def delete_unit(unit_id):
    with get_conn() as conn:
        execute(conn, "DELETE FROM units WHERE id=%s", (unit_id,))


def unit_is_available(unit_id, check_in, check_out, exclude_reservation_id=None):
    q = ("SELECT COUNT(*) AS cnt FROM reservations "
         "WHERE unit_id=%s AND status NOT IN ('cancelled','checked_out') "
         "AND check_in_date < %s AND check_out_date > %s")
    params = [unit_id, check_out, check_in]
    if exclude_reservation_id:
        q += " AND id != %s"
        params.append(exclude_reservation_id)
    with get_conn() as conn:
        row = fetchone(conn, q, params)
        return (row["cnt"] == 0) if row else True


# ── Guests ─────────────────────────────────────────────────────────────────────

def save_guest_id_document(guest_id, uploaded_file):
    os.makedirs(GUEST_DOCS_DIR, exist_ok=True)
    ext = os.path.splitext(uploaded_file.name)[1] or ".jpg"
    file_path = os.path.join(GUEST_DOCS_DIR, f"guest_{guest_id}_id{ext}")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path


def add_guest(account_id, full_name, phone="", email="", nationality="",
              id_number="", company="", special_requests=""):
    with get_conn() as conn:
        return lastrowid(conn,
            "INSERT INTO guests (account_id, full_name, phone, email, nationality, "
            "id_number, company, special_requests) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (account_id, full_name, phone, email, nationality, id_number, company, special_requests),
        )


def update_guest(guest_id, full_name, phone="", email="", nationality="",
                 id_number="", company="", special_requests=""):
    with get_conn() as conn:
        execute(conn,
            "UPDATE guests SET full_name=%s, phone=%s, email=%s, nationality=%s, "
            "id_number=%s, company=%s, special_requests=%s WHERE id=%s",
            (full_name, phone, email, nationality, id_number, company, special_requests, guest_id),
        )


def update_guest_id_document(guest_id, path):
    with get_conn() as conn:
        execute(conn, "UPDATE guests SET id_document_path=%s WHERE id=%s", (path, guest_id))


def list_guests(account_id=1):
    with get_conn() as conn:
        return fetchall(conn,
            "SELECT * FROM guests WHERE account_id=%s ORDER BY full_name",
            (account_id,),
        )


def get_guest(guest_id):
    with get_conn() as conn:
        return fetchone(conn, "SELECT * FROM guests WHERE id=%s", (guest_id,))


def search_guests(account_id, query):
    q = "%{}%".format(query)
    with get_conn() as conn:
        return fetchall(conn,
            "SELECT * FROM guests WHERE account_id=%s AND "
            "(full_name ILIKE %s OR phone ILIKE %s OR email ILIKE %s) ORDER BY full_name",
            (account_id, q, q, q),
        )


# ── Reservations ───────────────────────────────────────────────────────────────

def create_reservation(account_id, unit_id, guest_id, check_in_date, check_out_date,
                        num_guests, rate_type, rate_per_night, booking_source,
                        deposit_paid=0, special_requests="", notes=""):
    from datetime import datetime as dt
    ci = dt.strptime(check_in_date, "%Y-%m-%d").date()
    co = dt.strptime(check_out_date, "%Y-%m-%d").date()
    num_nights = (co - ci).days
    if num_nights < 1:
        raise ValueError("Check-out must be after check-in.")
    accommodation_total = rate_per_night * num_nights
    ref = _make_ref()
    with get_conn() as conn:
        rid = lastrowid(conn,
            "INSERT INTO reservations (account_id, booking_ref, unit_id, guest_id, "
            "check_in_date, check_out_date, num_guests, rate_type, rate_per_night, "
            "num_nights, accommodation_total, deposit_paid, booking_source, status, "
            "special_requests, notes) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'reserved',%s,%s) RETURNING id",
            (account_id, ref, unit_id, guest_id, check_in_date, check_out_date,
             num_guests, rate_type, rate_per_night, num_nights, accommodation_total,
             deposit_paid, booking_source, special_requests, notes),
        )
        execute(conn, "UPDATE units SET status='reserved' WHERE id=%s", (unit_id,))
        return rid, ref


def list_reservations(account_id=1, status=None, unit_id=None, date_from=None, date_to=None):
    q = ("SELECT r.*, g.full_name AS guest_name, g.phone AS guest_phone, "
         "u.unit_number, u.unit_type "
         "FROM reservations r "
         "JOIN guests g ON g.id = r.guest_id "
         "JOIN units u ON u.id = r.unit_id "
         "WHERE r.account_id = %s")
    params = [account_id]
    if status:
        q += " AND r.status = %s"; params.append(status)
    if unit_id:
        q += " AND r.unit_id = %s"; params.append(unit_id)
    if date_from:
        q += " AND r.check_out_date >= %s"; params.append(date_from)
    if date_to:
        q += " AND r.check_in_date <= %s"; params.append(date_to)
    q += " ORDER BY r.check_in_date DESC"
    with get_conn() as conn:
        return _san(fetchall(conn, q, params))


def get_reservation(reservation_id):
    with get_conn() as conn:
        return _san1(fetchone(conn,
            "SELECT r.*, g.full_name AS guest_name, g.phone AS guest_phone, "
            "g.email AS guest_email, u.unit_number, u.unit_type "
            "FROM reservations r "
            "JOIN guests g ON g.id = r.guest_id "
            "JOIN units u ON u.id = r.unit_id "
            "WHERE r.id = %s",
            (reservation_id,),
        ))


def check_in_reservation(reservation_id):
    with get_conn() as conn:
        row = fetchone(conn, "SELECT unit_id FROM reservations WHERE id=%s", (reservation_id,))
        execute(conn, "UPDATE reservations SET status='checked_in' WHERE id=%s", (reservation_id,))
        if row:
            execute(conn, "UPDATE units SET status='occupied' WHERE id=%s", (row["unit_id"],))


def check_out_reservation(reservation_id):
    with get_conn() as conn:
        row = fetchone(conn, "SELECT unit_id, guest_id, accommodation_total FROM reservations WHERE id=%s", (reservation_id,))
        execute(conn, "UPDATE reservations SET status='checked_out' WHERE id=%s", (reservation_id,))
        if row:
            execute(conn, "UPDATE units SET status='dirty' WHERE id=%s", (row["unit_id"],))
            execute(conn,
                "UPDATE guests SET total_stays=total_stays+1, total_spent=total_spent+%s WHERE id=%s",
                (row["accommodation_total"], row["guest_id"]),
            )
            acc_row = fetchone(conn, "SELECT account_id FROM units WHERE id=%s", (row["unit_id"],))
            if acc_row:
                execute(conn,
                    "INSERT INTO housekeeping (account_id, unit_id, task_type, status) VALUES (%s,%s,'checkout_clean','pending')",
                    (acc_row["account_id"], row["unit_id"]),
                )


def cancel_reservation(reservation_id):
    with get_conn() as conn:
        row = fetchone(conn, "SELECT unit_id FROM reservations WHERE id=%s", (reservation_id,))
        execute(conn, "UPDATE reservations SET status='cancelled' WHERE id=%s", (reservation_id,))
        if row:
            execute(conn, "UPDATE units SET status='available' WHERE id=%s", (row["unit_id"],))


# ── Folio items ────────────────────────────────────────────────────────────────

def add_folio_item(reservation_id, description, amount):
    with get_conn() as conn:
        return lastrowid(conn,
            "INSERT INTO folio_items (reservation_id, description, amount) VALUES (%s,%s,%s) RETURNING id",
            (reservation_id, description, amount),
        )


def list_folio_items(reservation_id):
    with get_conn() as conn:
        return fetchall(conn,
            "SELECT * FROM folio_items WHERE reservation_id=%s ORDER BY created_at",
            (reservation_id,),
        )


def delete_folio_item(item_id):
    with get_conn() as conn:
        execute(conn, "DELETE FROM folio_items WHERE id=%s", (item_id,))


def folio_summary(reservation_id):
    with get_conn() as conn:
        res = fetchone(conn,
            "SELECT accommodation_total, deposit_paid FROM reservations WHERE id=%s",
            (reservation_id,),
        )
        if not res:
            return {"accommodation": 0, "extras": 0, "total": 0, "paid": 0, "balance": 0}
        extras = scalar(conn,
            "SELECT COALESCE(SUM(amount),0) FROM folio_items WHERE reservation_id=%s",
            (reservation_id,),
        ) or 0
        paid = scalar(conn,
            "SELECT COALESCE(SUM(amount),0) FROM payments WHERE reservation_id=%s",
            (reservation_id,),
        ) or 0
        accommodation = res["accommodation_total"]
        total = accommodation + extras
        return {
            "accommodation": accommodation,
            "extras": extras,
            "total": total,
            "paid": paid,
            "balance": total - paid,
        }


# ── Payments ───────────────────────────────────────────────────────────────────

def record_payment(reservation_id, amount, payment_date, method,
                   momo_reference="", momo_provider="", payment_type="accommodation", note=""):
    with get_conn() as conn:
        return lastrowid(conn,
            "INSERT INTO payments (reservation_id, amount, payment_date, method, "
            "momo_reference, momo_provider, payment_type, note) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (reservation_id, amount, payment_date, method,
             momo_reference, momo_provider, payment_type, note),
        )


def list_payments(reservation_id=None, account_id=None, limit=None):
    q = ("SELECT p.*, r.booking_ref, g.full_name, u.unit_number, r.account_id "
         "FROM payments p "
         "JOIN reservations r ON r.id = p.reservation_id "
         "JOIN guests g ON g.id = r.guest_id "
         "JOIN units u ON u.id = r.unit_id "
         "WHERE 1=1")
    params = []
    if reservation_id:
        q += " AND p.reservation_id=%s"; params.append(reservation_id)
    if account_id:
        q += " AND r.account_id=%s"; params.append(account_id)
    q += " ORDER BY p.payment_date DESC"
    if limit:
        q += f" LIMIT {int(limit)}"
    with get_conn() as conn:
        return _san(fetchall(conn, q, params))


def get_payment(payment_id):
    with get_conn() as conn:
        return _san1(fetchone(conn,
            "SELECT p.*, r.booking_ref, g.full_name AS guest_name, u.unit_number, u.unit_type "
            "FROM payments p "
            "JOIN reservations r ON r.id = p.reservation_id "
            "JOIN guests g ON g.id = r.guest_id "
            "JOIN units u ON u.id = r.unit_id "
            "WHERE p.id=%s",
            (payment_id,),
        ))


# ── Housekeeping ───────────────────────────────────────────────────────────────

def list_housekeeping(account_id=1):
    with get_conn() as conn:
        return _san(fetchall(conn,
            "SELECT h.*, u.unit_number, u.unit_type, u.status AS unit_status "
            "FROM housekeeping h JOIN units u ON u.id=h.unit_id "
            "WHERE h.account_id=%s AND h.status != 'done' ORDER BY h.created_at DESC",
            (account_id,),
        ))


def update_housekeeping_status(task_id, status, assigned_to=""):
    completed_at = datetime.now().isoformat() if status == "done" else None
    with get_conn() as conn:
        execute(conn,
            "UPDATE housekeeping SET status=%s, assigned_to=%s, completed_at=%s WHERE id=%s",
            (status, assigned_to, completed_at, task_id),
        )


def create_housekeeping_task(account_id, unit_id, task_type="clean", assigned_to="", notes=""):
    with get_conn() as conn:
        return lastrowid(conn,
            "INSERT INTO housekeeping (account_id, unit_id, task_type, status, assigned_to, notes) "
            "VALUES (%s,%s,%s,'pending',%s,%s) RETURNING id",
            (account_id, unit_id, task_type, assigned_to, notes),
        )


# ── Maintenance ────────────────────────────────────────────────────────────────

def add_maintenance(account_id, unit_id, description, priority="medium", assigned_to="", cost=0, notes=""):
    with get_conn() as conn:
        rid = lastrowid(conn,
            "INSERT INTO maintenance (account_id, unit_id, description, priority, status, "
            "assigned_to, cost, notes) VALUES (%s,%s,%s,%s,'open',%s,%s,%s) RETURNING id",
            (account_id, unit_id, description, priority, assigned_to, cost, notes),
        )
        execute(conn,
            "UPDATE units SET status='maintenance', maintenance_status='needs_repair' WHERE id=%s",
            (unit_id,),
        )
        return rid


def list_maintenance(account_id=1, status=None):
    q = ("SELECT m.*, u.unit_number, u.unit_type FROM maintenance m "
         "JOIN units u ON u.id=m.unit_id WHERE m.account_id=%s")
    params = [account_id]
    if status:
        q += " AND m.status=%s"; params.append(status)
    q += " ORDER BY CASE m.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, m.reported_at DESC"
    with get_conn() as conn:
        return _san(fetchall(conn, q, params))


def resolve_maintenance(issue_id):
    with get_conn() as conn:
        row = fetchone(conn, "SELECT unit_id FROM maintenance WHERE id=%s", (issue_id,))
        execute(conn,
            "UPDATE maintenance SET status='resolved', resolved_at=%s WHERE id=%s",
            (datetime.now().isoformat(), issue_id),
        )
        if row:
            execute(conn,
                "UPDATE units SET status='available', maintenance_status='ok' WHERE id=%s",
                (row["unit_id"],),
            )


def update_maintenance(issue_id, description, priority, assigned_to, cost, notes):
    with get_conn() as conn:
        execute(conn,
            "UPDATE maintenance SET description=%s, priority=%s, assigned_to=%s, cost=%s, notes=%s WHERE id=%s",
            (description, priority, assigned_to, cost, notes, issue_id),
        )


# ── Expenses ───────────────────────────────────────────────────────────────────

def add_expense(account_id, category, description, amount, expense_date, note=""):
    with get_conn() as conn:
        return lastrowid(conn,
            "INSERT INTO expenses (account_id, category, description, amount, expense_date, note) "
            "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            (account_id, category, description, amount, expense_date, note),
        )


def list_expenses(account_id=1, month=None):
    q = "SELECT * FROM expenses WHERE account_id=%s"
    params = [account_id]
    if month:
        q += " AND expense_date LIKE %s"; params.append(f"{month}%")
    q += " ORDER BY expense_date DESC"
    with get_conn() as conn:
        return _san(fetchall(conn, q, params))


def delete_expense(expense_id):
    with get_conn() as conn:
        execute(conn, "DELETE FROM expenses WHERE id=%s", (expense_id,))


# ── Dashboard summary ──────────────────────────────────────────────────────────

def dashboard_summary(account_id=1):
    today = date.today().isoformat()
    month = today[:7]
    with get_conn() as conn:
        total_units = scalar(conn, "SELECT COUNT(*) FROM units WHERE account_id=%s", (account_id,)) or 0

        status_rows = fetchall(conn,
            "SELECT status, COUNT(*) AS cnt FROM units WHERE account_id=%s GROUP BY status",
            (account_id,),
        )
        sc = {r["status"]: r["cnt"] for r in status_rows}

        arrivals_today = scalar(conn,
            "SELECT COUNT(*) FROM reservations WHERE account_id=%s AND check_in_date=%s "
            "AND status IN ('reserved','checked_in')",
            (account_id, today),
        ) or 0
        departures_today = scalar(conn,
            "SELECT COUNT(*) FROM reservations WHERE account_id=%s AND check_out_date=%s "
            "AND status='checked_in'",
            (account_id, today),
        ) or 0
        month_revenue = scalar(conn,
            "SELECT COALESCE(SUM(p.amount),0) FROM payments p "
            "JOIN reservations r ON r.id=p.reservation_id "
            "WHERE r.account_id=%s AND p.payment_date LIKE %s",
            (account_id, f"{month}%"),
        ) or 0
        today_revenue = scalar(conn,
            "SELECT COALESCE(SUM(p.amount),0) FROM payments p "
            "JOIN reservations r ON r.id=p.reservation_id "
            "WHERE r.account_id=%s AND p.payment_date=%s",
            (account_id, today),
        ) or 0
        outstanding = scalar(conn,
            "SELECT COUNT(*) FROM reservations r WHERE r.account_id=%s "
            "AND r.status IN ('reserved','checked_in') "
            "AND (r.accommodation_total - COALESCE("
            "(SELECT SUM(p.amount) FROM payments p WHERE p.reservation_id=r.id),0)) > 0",
            (account_id,),
        ) or 0
        open_maintenance = scalar(conn,
            "SELECT COUNT(*) FROM maintenance WHERE account_id=%s AND status='open'",
            (account_id,),
        ) or 0
        pending_housekeeping = scalar(conn,
            "SELECT COUNT(*) FROM housekeeping WHERE account_id=%s AND status!='done'",
            (account_id,),
        ) or 0

    occupied = sc.get("occupied", 0)
    occupancy_pct = round((occupied / total_units * 100) if total_units else 0)
    return {
        "total_units": total_units,
        "occupied": sc.get("occupied", 0),
        "available": sc.get("available", 0),
        "reserved": sc.get("reserved", 0),
        "cleaning": sc.get("cleaning", 0) + sc.get("dirty", 0),
        "maintenance": sc.get("maintenance", 0),
        "arrivals_today": arrivals_today,
        "departures_today": departures_today,
        "today_revenue": today_revenue,
        "month_revenue": month_revenue,
        "occupancy_pct": occupancy_pct,
        "outstanding_balances": outstanding,
        "open_maintenance": open_maintenance,
        "pending_housekeeping": pending_housekeeping,
    }


# ── Reports ────────────────────────────────────────────────────────────────────

def revenue_by_source(account_id, month=None):
    q = ("SELECT r.booking_source, COALESCE(SUM(p.amount),0) AS total, COUNT(DISTINCT r.id) AS bookings "
         "FROM reservations r LEFT JOIN payments p ON p.reservation_id=r.id "
         "WHERE r.account_id=%s")
    params = [account_id]
    if month:
        q += " AND r.check_in_date LIKE %s"; params.append(f"{month}%")
    q += " GROUP BY r.booking_source ORDER BY total DESC"
    with get_conn() as conn:
        return _san(fetchall(conn, q, params))


def monthly_summary(account_id, month):
    with get_conn() as conn:
        revenue = scalar(conn,
            "SELECT COALESCE(SUM(p.amount),0) FROM payments p "
            "JOIN reservations r ON r.id=p.reservation_id "
            "WHERE r.account_id=%s AND p.payment_date LIKE %s",
            (account_id, f"{month}%"),
        ) or 0
        expenses = scalar(conn,
            "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE account_id=%s AND expense_date LIKE %s",
            (account_id, f"{month}%"),
        ) or 0
        bookings = scalar(conn,
            "SELECT COUNT(*) FROM reservations WHERE account_id=%s AND check_in_date LIKE %s",
            (account_id, f"{month}%"),
        ) or 0
        nights_sold = scalar(conn,
            "SELECT COALESCE(SUM(num_nights),0) FROM reservations "
            "WHERE account_id=%s AND check_in_date LIKE %s AND status != 'cancelled'",
            (account_id, f"{month}%"),
        ) or 0
    return {
        "month": month,
        "revenue": revenue,
        "expenses": expenses,
        "net": revenue - expenses,
        "bookings": bookings,
        "nights_sold": nights_sold,
    }
