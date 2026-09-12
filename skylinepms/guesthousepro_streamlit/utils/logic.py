"""
Business logic for GuesthousePro.
Units, guests, reservations, folios, payments, housekeeping, maintenance, expenses.
"""
import os
import secrets
from datetime import date, datetime
from utils.db import get_conn

GUEST_DOCS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "guest_documents"
)

UNIT_TYPES = ["2 Bedroom", "1 Bedroom", "Bachelor Studio", "Suite", "Standard", "Other"]
UNIT_STATUSES = ["available", "occupied", "reserved", "cleaning", "maintenance", "dirty", "inspected"]
BOOKING_SOURCES = [
    "Direct WhatsApp", "Phone Call", "Walk-in", "Website", "Facebook",
    "Instagram", "Airbnb", "Booking.com", "Referral", "Corporate",
    "Travel Agent", "Other",
]
PAYMENT_METHODS = ["cash", "mobile_money", "bank", "card", "other"]
EXPENSE_CATEGORIES = [
    "Electricity", "Water", "Internet/WiFi", "Cleaning Supplies",
    "Maintenance", "Staff", "Laundry", "Marketing", "Other",
]


# ---------- Booking reference ----------

def _make_ref(account_id):
    year = datetime.now().strftime("%Y")
    rand = secrets.token_hex(3).upper()
    return f"GHP-{year}-{rand}"


# ---------- Units ----------

def add_unit(account_id, unit_number, unit_type, floor, max_guests,
             rate_nightly, rate_weekend, rate_monthly, amenities="", notes=""):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO units (account_id, unit_number, unit_type, floor, max_guests,
               rate_nightly, rate_weekend, rate_monthly, amenities, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (account_id, unit_number, unit_type, floor, max_guests,
             rate_nightly, rate_weekend, rate_monthly, amenities, notes),
        )
        return cur.lastrowid


def list_units(account_id=1):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM units WHERE account_id = ? ORDER BY unit_number",
            (account_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_unit(unit_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM units WHERE id = ?", (unit_id,)).fetchone()
        return dict(row) if row else None


def update_unit(unit_id, unit_number, unit_type, floor, max_guests,
                rate_nightly, rate_weekend, rate_monthly, amenities="", notes=""):
    with get_conn() as conn:
        conn.execute(
            """UPDATE units SET unit_number=?, unit_type=?, floor=?, max_guests=?,
               rate_nightly=?, rate_weekend=?, rate_monthly=?, amenities=?, notes=?
               WHERE id=?""",
            (unit_number, unit_type, floor, max_guests,
             rate_nightly, rate_weekend, rate_monthly, amenities, notes, unit_id),
        )


def update_unit_status(unit_id, status):
    with get_conn() as conn:
        conn.execute("UPDATE units SET status = ? WHERE id = ?", (status, unit_id))


def delete_unit(unit_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM units WHERE id = ?", (unit_id,))


def unit_is_available(unit_id, check_in, check_out, exclude_reservation_id=None):
    """Return True if unit has no overlapping confirmed/reserved/occupied bookings."""
    with get_conn() as conn:
        q = """SELECT COUNT(*) cnt FROM reservations
               WHERE unit_id = ?
               AND status NOT IN ('cancelled', 'checked_out')
               AND check_in_date < ? AND check_out_date > ?"""
        params = [unit_id, check_out, check_in]
        if exclude_reservation_id:
            q += " AND id != ?"
            params.append(exclude_reservation_id)
        row = conn.execute(q, params).fetchone()
        return row["cnt"] == 0


# ---------- Guests ----------

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
        cur = conn.execute(
            """INSERT INTO guests (account_id, full_name, phone, email, nationality,
               id_number, company, special_requests)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (account_id, full_name, phone, email, nationality, id_number, company, special_requests),
        )
        return cur.lastrowid


def update_guest(guest_id, full_name, phone="", email="", nationality="",
                 id_number="", company="", special_requests=""):
    with get_conn() as conn:
        conn.execute(
            """UPDATE guests SET full_name=?, phone=?, email=?, nationality=?,
               id_number=?, company=?, special_requests=? WHERE id=?""",
            (full_name, phone, email, nationality, id_number, company, special_requests, guest_id),
        )


def update_guest_id_document(guest_id, path):
    with get_conn() as conn:
        conn.execute("UPDATE guests SET id_document_path=? WHERE id=?", (path, guest_id))


def list_guests(account_id=1):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM guests WHERE account_id = ? ORDER BY full_name",
            (account_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_guest(guest_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM guests WHERE id = ?", (guest_id,)).fetchone()
        return dict(row) if row else None


def search_guests(account_id, query):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM guests WHERE account_id = ? AND (full_name LIKE ? OR phone LIKE ? OR email LIKE ?) ORDER BY full_name",
            (account_id, f"%{query}%", f"%{query}%", f"%{query}%"),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- Reservations ----------

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
    ref = _make_ref(account_id)
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO reservations (account_id, booking_ref, unit_id, guest_id,
               check_in_date, check_out_date, num_guests, rate_type, rate_per_night,
               num_nights, accommodation_total, deposit_paid, booking_source,
               status, special_requests, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'reserved', ?, ?)""",
            (account_id, ref, unit_id, guest_id, check_in_date, check_out_date,
             num_guests, rate_type, rate_per_night, num_nights, accommodation_total,
             deposit_paid, booking_source, special_requests, notes),
        )
        conn.execute("UPDATE units SET status='reserved' WHERE id=?", (unit_id,))
        return cur.lastrowid, ref


def list_reservations(account_id=1, status=None, unit_id=None, date_from=None, date_to=None):
    with get_conn() as conn:
        q = """SELECT r.*, g.full_name as guest_name, g.phone as guest_phone,
                      u.unit_number, u.unit_type
               FROM reservations r
               JOIN guests g ON g.id = r.guest_id
               JOIN units u ON u.id = r.unit_id
               WHERE r.account_id = ?"""
        params = [account_id]
        if status:
            q += " AND r.status = ?"
            params.append(status)
        if unit_id:
            q += " AND r.unit_id = ?"
            params.append(unit_id)
        if date_from:
            q += " AND r.check_out_date >= ?"
            params.append(date_from)
        if date_to:
            q += " AND r.check_in_date <= ?"
            params.append(date_to)
        q += " ORDER BY r.check_in_date DESC"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def get_reservation(reservation_id):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT r.*, g.full_name as guest_name, g.phone as guest_phone,
                      g.email as guest_email, u.unit_number, u.unit_type
               FROM reservations r
               JOIN guests g ON g.id = r.guest_id
               JOIN units u ON u.id = r.unit_id
               WHERE r.id = ?""",
            (reservation_id,),
        ).fetchone()
        return dict(row) if row else None


def check_in_reservation(reservation_id):
    with get_conn() as conn:
        row = conn.execute("SELECT unit_id FROM reservations WHERE id=?", (reservation_id,)).fetchone()
        conn.execute("UPDATE reservations SET status='checked_in' WHERE id=?", (reservation_id,))
        if row:
            conn.execute("UPDATE units SET status='occupied' WHERE id=?", (row["unit_id"],))


def check_out_reservation(reservation_id):
    with get_conn() as conn:
        row = conn.execute("SELECT unit_id, guest_id FROM reservations WHERE id=?", (reservation_id,)).fetchone()
        conn.execute("UPDATE reservations SET status='checked_out' WHERE id=?", (reservation_id,))
        if row:
            # Mark unit as dirty → housekeeping needed
            conn.execute("UPDATE units SET status='dirty' WHERE id=?", (row["unit_id"],))
            # Update guest stats
            res = conn.execute(
                "SELECT accommodation_total FROM reservations WHERE id=?", (reservation_id,)
            ).fetchone()
            if res:
                conn.execute(
                    "UPDATE guests SET total_stays = total_stays+1, total_spent = total_spent+? WHERE id=?",
                    (res["accommodation_total"], row["guest_id"]),
                )
            # Log a housekeeping task
            conn.execute(
                "INSERT INTO housekeeping (account_id, unit_id, task_type, status) SELECT account_id, ?, 'checkout_clean', 'pending' FROM units WHERE id=?",
                (row["unit_id"], row["unit_id"]),
            )


def cancel_reservation(reservation_id):
    with get_conn() as conn:
        row = conn.execute("SELECT unit_id FROM reservations WHERE id=?", (reservation_id,)).fetchone()
        conn.execute("UPDATE reservations SET status='cancelled' WHERE id=?", (reservation_id,))
        if row:
            conn.execute("UPDATE units SET status='available' WHERE id=?", (row["unit_id"],))


def update_reservation_notes(reservation_id, notes):
    with get_conn() as conn:
        conn.execute("UPDATE reservations SET notes=? WHERE id=?", (notes, reservation_id))


# ---------- Folio items ----------

def add_folio_item(reservation_id, description, amount):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO folio_items (reservation_id, description, amount) VALUES (?, ?, ?)",
            (reservation_id, description, amount),
        )
        return cur.lastrowid


def list_folio_items(reservation_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM folio_items WHERE reservation_id=? ORDER BY created_at",
            (reservation_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def delete_folio_item(item_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM folio_items WHERE id=?", (item_id,))


def folio_summary(reservation_id):
    with get_conn() as conn:
        res = conn.execute(
            "SELECT accommodation_total, deposit_paid FROM reservations WHERE id=?",
            (reservation_id,),
        ).fetchone()
        if not res:
            return {"accommodation": 0, "extras": 0, "total": 0, "paid": 0, "balance": 0}
        extras_row = conn.execute(
            "SELECT COALESCE(SUM(amount),0) total FROM folio_items WHERE reservation_id=?",
            (reservation_id,),
        ).fetchone()
        paid_row = conn.execute(
            "SELECT COALESCE(SUM(amount),0) total FROM payments WHERE reservation_id=?",
            (reservation_id,),
        ).fetchone()
        accommodation = res["accommodation_total"]
        extras = extras_row["total"] if extras_row else 0
        total = accommodation + extras
        paid  = paid_row["total"] if paid_row else 0
        return {
            "accommodation": accommodation,
            "extras": extras,
            "total": total,
            "paid": paid,
            "balance": total - paid,
        }


# ---------- Payments ----------

def record_payment(reservation_id, amount, payment_date, method,
                   momo_reference="", momo_provider="", payment_type="accommodation", note=""):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO payments (reservation_id, amount, payment_date, method,
               momo_reference, momo_provider, payment_type, note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (reservation_id, amount, payment_date, method,
             momo_reference, momo_provider, payment_type, note),
        )
        return cur.lastrowid


def list_payments(reservation_id=None, account_id=None, limit=None):
    with get_conn() as conn:
        q = """SELECT p.*, r.booking_ref, g.full_name as guest_name,
                      u.unit_number, r.account_id
               FROM payments p
               JOIN reservations r ON r.id = p.reservation_id
               JOIN guests g ON g.id = r.guest_id
               JOIN units u ON u.id = r.unit_id
               WHERE 1=1"""
        params = []
        if reservation_id:
            q += " AND p.reservation_id = ?"
            params.append(reservation_id)
        if account_id:
            q += " AND r.account_id = ?"
            params.append(account_id)
        q += " ORDER BY p.payment_date DESC"
        if limit:
            q += f" LIMIT {int(limit)}"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def get_payment(payment_id):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT p.*, r.booking_ref, g.full_name, u.unit_number, u.unit_type
               FROM payments p
               JOIN reservations r ON r.id = p.reservation_id
               JOIN guests g ON g.id = r.guest_id
               JOIN units u ON u.id = r.unit_id
               WHERE p.id=?""",
            (payment_id,),
        ).fetchone()
        return dict(row) if row else None


# ---------- Housekeeping ----------

def list_housekeeping(account_id=1):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT h.*, u.unit_number, u.unit_type, u.status as unit_status
               FROM housekeeping h
               JOIN units u ON u.id = h.unit_id
               WHERE h.account_id = ? AND h.status != 'done'
               ORDER BY h.created_at DESC""",
            (account_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def update_housekeeping_status(task_id, status, assigned_to=""):
    with get_conn() as conn:
        completed_at = datetime.now().isoformat() if status == "done" else None
        conn.execute(
            "UPDATE housekeeping SET status=?, assigned_to=?, completed_at=? WHERE id=?",
            (status, assigned_to, completed_at, task_id),
        )


def create_housekeeping_task(account_id, unit_id, task_type="clean", assigned_to="", notes=""):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO housekeeping (account_id, unit_id, task_type, status, assigned_to, notes) VALUES (?,?,?,'pending',?,?)",
            (account_id, unit_id, task_type, assigned_to, notes),
        )
        return cur.lastrowid


# ---------- Maintenance ----------

def add_maintenance(account_id, unit_id, description, priority="medium", assigned_to="", cost=0, notes=""):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO maintenance (account_id, unit_id, description, priority, status,
               assigned_to, cost, notes) VALUES (?, ?, ?, ?, 'open', ?, ?, ?)""",
            (account_id, unit_id, description, priority, assigned_to, cost, notes),
        )
        # Block the unit
        conn.execute("UPDATE units SET status='maintenance', maintenance_status='needs_repair' WHERE id=?", (unit_id,))
        return cur.lastrowid


def list_maintenance(account_id=1, status=None):
    with get_conn() as conn:
        q = """SELECT m.*, u.unit_number, u.unit_type FROM maintenance m
               JOIN units u ON u.id = m.unit_id
               WHERE m.account_id = ?"""
        params = [account_id]
        if status:
            q += " AND m.status = ?"
            params.append(status)
        q += " ORDER BY CASE m.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, m.reported_at DESC"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def resolve_maintenance(issue_id):
    with get_conn() as conn:
        row = conn.execute("SELECT unit_id FROM maintenance WHERE id=?", (issue_id,)).fetchone()
        conn.execute(
            "UPDATE maintenance SET status='resolved', resolved_at=? WHERE id=?",
            (datetime.now().isoformat(), issue_id),
        )
        if row:
            conn.execute("UPDATE units SET status='available', maintenance_status='ok' WHERE id=?", (row["unit_id"],))


def update_maintenance(issue_id, description, priority, assigned_to, cost, notes):
    with get_conn() as conn:
        conn.execute(
            "UPDATE maintenance SET description=?, priority=?, assigned_to=?, cost=?, notes=? WHERE id=?",
            (description, priority, assigned_to, cost, notes, issue_id),
        )


# ---------- Expenses ----------

def add_expense(account_id, category, description, amount, expense_date, note=""):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO expenses (account_id, category, description, amount, expense_date, note) VALUES (?,?,?,?,?,?)",
            (account_id, category, description, amount, expense_date, note),
        )
        return cur.lastrowid


def list_expenses(account_id=1, month=None):
    with get_conn() as conn:
        q = "SELECT * FROM expenses WHERE account_id = ?"
        params = [account_id]
        if month:
            q += " AND expense_date LIKE ?"
            params.append(f"{month}%")
        q += " ORDER BY expense_date DESC"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def delete_expense(expense_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM expenses WHERE id=?", (expense_id,))


# ---------- Dashboard summary ----------

def dashboard_summary(account_id=1):
    today = date.today().isoformat()
    with get_conn() as conn:
        total_units = conn.execute("SELECT COUNT(*) cnt FROM units WHERE account_id=?", (account_id,)).fetchone()["cnt"]
        status_counts = {}
        for row in conn.execute("SELECT status, COUNT(*) cnt FROM units WHERE account_id=? GROUP BY status", (account_id,)).fetchall():
            status_counts[row["status"]] = row["cnt"]

        arrivals_today = conn.execute(
            "SELECT COUNT(*) cnt FROM reservations r JOIN units u ON u.id=r.unit_id WHERE r.account_id=? AND r.check_in_date=? AND r.status IN ('reserved','checked_in')",
            (account_id, today),
        ).fetchone()["cnt"]
        departures_today = conn.execute(
            "SELECT COUNT(*) cnt FROM reservations r JOIN units u ON u.id=r.unit_id WHERE r.account_id=? AND r.check_out_date=? AND r.status='checked_in'",
            (account_id, today),
        ).fetchone()["cnt"]

        month = today[:7]
        month_revenue = conn.execute(
            """SELECT COALESCE(SUM(p.amount),0) total FROM payments p
               JOIN reservations r ON r.id=p.reservation_id
               WHERE r.account_id=? AND p.payment_date LIKE ?""",
            (account_id, f"{month}%"),
        ).fetchone()["total"]
        today_revenue = conn.execute(
            """SELECT COALESCE(SUM(p.amount),0) total FROM payments p
               JOIN reservations r ON r.id=p.reservation_id
               WHERE r.account_id=? AND p.payment_date=?""",
            (account_id, today),
        ).fetchone()["total"]

        outstanding = conn.execute(
            """SELECT COUNT(*) cnt FROM reservations r
               WHERE r.account_id=? AND r.status IN ('reserved','checked_in')
               AND (r.accommodation_total - COALESCE((SELECT SUM(p.amount) FROM payments p WHERE p.reservation_id=r.id),0)) > 0""",
            (account_id,),
        ).fetchone()["cnt"]

        open_maintenance = conn.execute(
            "SELECT COUNT(*) cnt FROM maintenance WHERE account_id=? AND status='open'", (account_id,)
        ).fetchone()["cnt"]

        pending_housekeeping = conn.execute(
            "SELECT COUNT(*) cnt FROM housekeeping WHERE account_id=? AND status!='done'", (account_id,)
        ).fetchone()["cnt"]

    occupied = status_counts.get("occupied", 0)
    occupancy_pct = round((occupied / total_units * 100) if total_units else 0)

    return {
        "total_units": total_units,
        "occupied": status_counts.get("occupied", 0),
        "available": status_counts.get("available", 0),
        "reserved": status_counts.get("reserved", 0),
        "cleaning": status_counts.get("cleaning", 0) + status_counts.get("dirty", 0),
        "maintenance": status_counts.get("maintenance", 0),
        "arrivals_today": arrivals_today,
        "departures_today": departures_today,
        "today_revenue": today_revenue,
        "month_revenue": month_revenue,
        "occupancy_pct": occupancy_pct,
        "outstanding_balances": outstanding,
        "open_maintenance": open_maintenance,
        "pending_housekeeping": pending_housekeeping,
    }


# ---------- Reports ----------

def revenue_by_source(account_id, month=None):
    with get_conn() as conn:
        q = """SELECT r.booking_source, COALESCE(SUM(p.amount),0) total, COUNT(DISTINCT r.id) bookings
               FROM reservations r
               LEFT JOIN payments p ON p.reservation_id=r.id
               WHERE r.account_id=?"""
        params = [account_id]
        if month:
            q += " AND r.check_in_date LIKE ?"
            params.append(f"{month}%")
        q += " GROUP BY r.booking_source ORDER BY total DESC"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def monthly_summary(account_id, month):
    with get_conn() as conn:
        revenue = conn.execute(
            """SELECT COALESCE(SUM(p.amount),0) total FROM payments p
               JOIN reservations r ON r.id=p.reservation_id
               WHERE r.account_id=? AND p.payment_date LIKE ?""",
            (account_id, f"{month}%"),
        ).fetchone()["total"]
        expenses = conn.execute(
            "SELECT COALESCE(SUM(amount),0) total FROM expenses WHERE account_id=? AND expense_date LIKE ?",
            (account_id, f"{month}%"),
        ).fetchone()["total"]
        bookings = conn.execute(
            "SELECT COUNT(*) cnt FROM reservations WHERE account_id=? AND check_in_date LIKE ?",
            (account_id, f"{month}%"),
        ).fetchone()["cnt"]
        nights_sold = conn.execute(
            "SELECT COALESCE(SUM(num_nights),0) total FROM reservations WHERE account_id=? AND check_in_date LIKE ? AND status != 'cancelled'",
            (account_id, f"{month}%"),
        ).fetchone()["total"]
    return {
        "month": month,
        "revenue": revenue,
        "expenses": expenses,
        "net": revenue - expenses,
        "bookings": bookings,
        "nights_sold": nights_sold,
    }
