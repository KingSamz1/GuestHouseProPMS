"""
WhatsApp guest messaging for GuesthousePro — PostgreSQL version.
"""
import urllib.parse
from utils.db import get_conn, get_account
from utils.pg import fetchone, execute


def _property_name(account_id):
    acc = get_account(account_id)
    return (acc or {}).get("property_name", "the property")


def _get_res(reservation_id):
    with get_conn() as conn:
        return fetchone(conn,
            "SELECT r.*, g.full_name, g.phone AS guest_phone, u.unit_number, u.unit_type "
            "FROM reservations r "
            "JOIN guests g ON g.id=r.guest_id "
            "JOIN units u ON u.id=r.unit_id "
            "WHERE r.id=%s",
            (reservation_id,),
        )


def build_booking_confirmation(reservation_id):
    row = _get_res(reservation_id)
    if not row: return ""
    prop = _property_name(row["account_id"])
    return (
        f"Dear {row['full_name']}, thank you for choosing {prop}. "
        f"Your booking {row['booking_ref']} for {row['unit_type']} (Unit {row['unit_number']}) "
        f"is confirmed: check-in {row['check_in_date']}, check-out {row['check_out_date']} "
        f"({row['num_nights']} night(s)). We look forward to welcoming you!"
    )


def build_arrival_reminder(reservation_id):
    row = _get_res(reservation_id)
    if not row: return ""
    prop = _property_name(row["account_id"])
    return (
        f"Dear {row['full_name']}, this is a reminder that your check-in at {prop} "
        f"({row['unit_type']}, Unit {row['unit_number']}) is tomorrow, {row['check_in_date']}. "
        f"We look forward to welcoming you."
    )


def build_checkout_reminder(reservation_id):
    row = _get_res(reservation_id)
    if not row: return ""
    prop = _property_name(row["account_id"])
    return (
        f"Good morning {row['full_name']}. Your checkout from {prop} (Unit {row['unit_number']}) "
        f"is scheduled for today, {row['check_out_date']}. Checkout time is 11:00 AM. Thank you!"
    )


def build_post_checkout_message(reservation_id):
    row = _get_res(reservation_id)
    if not row: return ""
    prop = _property_name(row["account_id"])
    return (
        f"Dear {row['full_name']}, thank you for staying with us at {prop}. "
        f"We hope you enjoyed your stay and we look forward to welcoming you back!"
    )


def build_balance_reminder(reservation_id, balance, currency="UGX"):
    row = _get_res(reservation_id)
    if not row: return ""
    prop = _property_name(row["account_id"])
    return (
        f"Dear {row['full_name']}, this is a reminder from {prop}. "
        f"Your booking {row['booking_ref']} has an outstanding balance of "
        f"{currency} {balance:,.0f}. Kindly settle at your earliest convenience. Thank you."
    )


def log_message(reservation_id, message_type, message):
    with get_conn() as conn:
        execute(conn,
            "INSERT INTO messages_log (reservation_id, message_type, message) VALUES (%s,%s,%s)",
            (reservation_id, message_type, message),
        )


def whatsapp_link(phone, message):
    clean_phone = "".join(ch for ch in phone if ch.isdigit())
    return f"https://wa.me/{clean_phone}?text={urllib.parse.quote(message)}"
