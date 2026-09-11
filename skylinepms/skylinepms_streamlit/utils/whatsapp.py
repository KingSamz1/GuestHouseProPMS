"""
WhatsApp guest messaging for SkylinePMS.
Builds confirmation, reminder, and post-checkout messages.
Manual send via click-to-chat link; automated sending can be wired to the
WhatsApp Business API or Twilio when ready.
"""
import urllib.parse
from utils.db import get_conn, get_account


def _property_name(account_id):
    acc = get_account(account_id)
    return (acc or {}).get("property_name", "the property")


def build_booking_confirmation(reservation_id):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT r.booking_ref, r.check_in_date, r.check_out_date, r.num_nights,
                      r.accommodation_total, r.account_id,
                      g.full_name, u.unit_number, u.unit_type
               FROM reservations r
               JOIN guests g ON g.id=r.guest_id
               JOIN units u ON u.id=r.unit_id
               WHERE r.id=?""",
            (reservation_id,),
        ).fetchone()
    if not row:
        return ""
    prop = _property_name(row["account_id"])
    return (
        f"Dear {row['full_name']}, thank you for choosing {prop}. "
        f"Your booking {row['booking_ref']} for {row['unit_type']} (Unit {row['unit_number']}) "
        f"is confirmed: check-in {row['check_in_date']}, check-out {row['check_out_date']} "
        f"({row['num_nights']} night(s)). We look forward to welcoming you!"
    )


def build_arrival_reminder(reservation_id):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT r.check_in_date, r.account_id, g.full_name, u.unit_number, u.unit_type
               FROM reservations r
               JOIN guests g ON g.id=r.guest_id
               JOIN units u ON u.id=r.unit_id
               WHERE r.id=?""",
            (reservation_id,),
        ).fetchone()
    if not row:
        return ""
    prop = _property_name(row["account_id"])
    return (
        f"Dear {row['full_name']}, this is a reminder that your check-in at {prop} "
        f"({row['unit_type']}, Unit {row['unit_number']}) is tomorrow, {row['check_in_date']}. "
        f"We look forward to welcoming you. Please don't hesitate to reach out if you need anything."
    )


def build_checkout_reminder(reservation_id):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT r.check_out_date, r.account_id, g.full_name, u.unit_number
               FROM reservations r
               JOIN guests g ON g.id=r.guest_id
               JOIN units u ON u.id=r.unit_id
               WHERE r.id=?""",
            (reservation_id,),
        ).fetchone()
    if not row:
        return ""
    prop = _property_name(row["account_id"])
    return (
        f"Good morning {row['full_name']}. Your checkout from {prop} (Unit {row['unit_number']}) "
        f"is scheduled for today, {row['check_out_date']}. "
        f"Checkout time is 11:00 AM. Thank you for staying with us!"
    )


def build_post_checkout_message(reservation_id):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT r.account_id, g.full_name
               FROM reservations r
               JOIN guests g ON g.id=r.guest_id
               WHERE r.id=?""",
            (reservation_id,),
        ).fetchone()
    if not row:
        return ""
    prop = _property_name(row["account_id"])
    return (
        f"Dear {row['full_name']}, thank you for staying with us at {prop}. "
        f"We hope you enjoyed your stay. We'd love to hear your feedback — "
        f"and we hope to welcome you back soon!"
    )


def build_balance_reminder(reservation_id, balance, currency="UGX"):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT r.booking_ref, r.account_id, g.full_name
               FROM reservations r
               JOIN guests g ON g.id=r.guest_id
               WHERE r.id=?""",
            (reservation_id,),
        ).fetchone()
    if not row:
        return ""
    prop = _property_name(row["account_id"])
    return (
        f"Dear {row['full_name']}, this is a reminder from {prop}. "
        f"Your booking {row['booking_ref']} has an outstanding balance of "
        f"{currency} {balance:,.0f}. Kindly settle at your earliest convenience. Thank you."
    )


def log_message(reservation_id, message_type, message):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages_log (reservation_id, message_type, message) VALUES (?,?,?)",
            (reservation_id, message_type, message),
        )


def whatsapp_link(phone, message):
    clean_phone = "".join(ch for ch in phone if ch.isdigit())
    return f"https://wa.me/{clean_phone}?text={urllib.parse.quote(message)}"
