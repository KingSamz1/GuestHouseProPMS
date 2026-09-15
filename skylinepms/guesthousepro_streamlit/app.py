import streamlit as st
from datetime import date
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.logic import dashboard_summary, list_reservations, list_payments
from utils.theme import apply_theme, page_header, section_label, empty_state, subscription_banner, metric_row, status_pill, colors

st.set_page_config(page_title="GuesthousePro", page_icon="🏨", layout="wide")
apply_theme()
init_db()

if not check_login():
    st.stop()

account_id = get_current_account_id()
account    = get_account(account_id)
logout_button()

property_name = account["property_name"] if account else "My Property"
currency      = account["currency"] if account else "UGX"
c = colors()

page_header(property_name, subtitle=f"Management Dashboard · {date.today().strftime('%A, %d %B %Y')}", icon="🏨")
subscription_banner()
st.write("")

summary = dashboard_summary(account_id=account_id)

# ── Occupancy row ──────────────────────────────────────────────────────────────
metric_row([
    {"label": "Total Units",       "value": str(summary["total_units"]),       "tone": "neutral"},
    {"label": "🟢 Occupied",        "value": str(summary["occupied"]),          "tone": "accent"},
    {"label": "✅ Available",       "value": str(summary["available"]),         "tone": "success"},
    {"label": "🔖 Reserved",        "value": str(summary["reserved"]),          "tone": "warning"},
    {"label": "🧹 Cleaning/Dirty",  "value": str(summary["cleaning"]),          "tone": "warning"},
    {"label": "🔧 Maintenance",     "value": str(summary["maintenance"]),       "tone": "danger"},
])

# ── Revenue row ────────────────────────────────────────────────────────────────
metric_row([
    {"label": "Occupancy Today",   "value": f"{summary['occupancy_pct']}%",                          "tone": "accent"},
    {"label": "Today's Revenue",   "value": f"{currency} {summary['today_revenue']:,.0f}",           "tone": "accent"},
    {"label": "This Month Revenue","value": f"{currency} {summary['month_revenue']:,.0f}",           "tone": "accent"},
    {"label": "Outstanding Balances","value": str(summary["outstanding_balances"]),                  "tone": "danger"},
])

# ── Today's activity ──────────────────────────────────────────────────────────
st.write("")
section_label("Today's activity")
today_str = date.today().isoformat()
col_a, col_b, col_c, col_d = st.columns(4)

def _action_card(col, icon, label, value, tone):
    bg_map = {"green": c["SUCCESS_SOFT"], "red": c["DANGER_SOFT"], "blue": c["ACCENT_SOFT"], "yellow": c["WARNING_SOFT"]}
    col_map = {"green": c["SUCCESS"], "red": c["DANGER"], "blue": c["ACCENT_DARK"], "yellow": c["WARNING"]}
    bg  = bg_map.get(tone, c["NEUTRAL_SOFT"])
    clr = col_map.get(tone, c["TEXT_MUTED"])
    col.markdown(
        f'<div style="background:{bg}; border-radius:12px; padding:1rem 1.1rem; text-align:center;">'
        f'<div style="font-size:1.8rem;">{icon}</div>'
        f'<div style="font-size:26px; font-weight:700; color:{clr};">{value}</div>'
        f'<div style="font-size:12px; color:{c["TEXT_MUTED"]}; margin-top:2px;">{label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

_action_card(col_a, "🛬", "Arrivals Today",          summary["arrivals_today"],          "green")
_action_card(col_b, "🛫", "Departures Today",         summary["departures_today"],         "red")
_action_card(col_c, "🧹", "Housekeeping Tasks",       summary["pending_housekeeping"],     "yellow")
_action_card(col_d, "🔧", "Open Maintenance",         summary["open_maintenance"],         "red")

st.write("")

# ── Quick actions ──────────────────────────────────────────────────────────────
section_label("Quick actions")
qa1, qa2, qa3, qa4, qa5, qa6 = st.columns(6)
with qa1:
    if st.button("📅 New Booking", use_container_width=True, help="Create a new reservation"):
        st.switch_page("pages/2_📅_Reservations.py")
with qa2:
    if st.button("🛬 Check In/Out", use_container_width=True, help="Arrivals & departures"):
        st.switch_page("pages/4_🛎️_Check_In_Out.py")
with qa3:
    if st.button("🧾 Guest Bill", use_container_width=True, help="View or update a guest's bill"):
        st.switch_page("pages/5_💰_Billing.py")
with qa4:
    if st.button("💳 Record Payment", use_container_width=True, help="Record a cash or MoMo payment"):
        st.switch_page("pages/5_💰_Billing.py")
with qa5:
    if st.button("🧹 Housekeeping", use_container_width=True, help="Room cleaning status board"):
        st.switch_page("pages/6_🧹_Housekeeping.py")
with qa6:
    if st.button("📊 Reports", use_container_width=True, help="Revenue, occupancy & booking sources"):
        st.switch_page("pages/9_📊_Reports.py")

st.divider()

# ── Two-column layout: today's bookings + recent payments ─────────────────────
left, right = st.columns([1, 1], gap="large")

with left:
    section_label("Today's arrivals & departures")
    today_bookings = list_reservations(account_id=account_id, date_from=today_str, date_to=today_str)
    if not today_bookings:
        empty_state("No arrivals or departures today.", icon="📅")
    else:
        rows_html = ""
        for r in today_bookings[:8]:
            if r["check_in_date"] == today_str:
                icon = "🛬"; label = f"Arriving — Unit {r['unit_number']}"
            else:
                icon = "🛫"; label = f"Departing — Unit {r['unit_number']}"
            tone = "success" if r["status"] == "checked_in" else "warning"
            pill = status_pill(r["status"].replace("_", " ").title(), tone)
            rows_html += (
                f'<div style="display:flex; justify-content:space-between; align-items:center; '
                f'padding:9px 0; border-bottom:1px solid {c["BORDER"]};">'
                f'<div>'
                f'<div style="font-size:13px; font-weight:500;">{icon} {r["guest_name"]}</div>'
                f'<div style="font-size:11px; color:{c["TEXT_MUTED"]};">{label} · {r["booking_ref"]}</div>'
                f'</div>{pill}</div>'
            )
        st.markdown(
            f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
            f'border-radius:14px; padding:0.25rem 1.1rem;">{rows_html}</div>',
            unsafe_allow_html=True,
        )

with right:
    section_label("Recent payments")
    recent_payments = list_payments(account_id=account_id, limit=7)
    if not recent_payments:
        empty_state("No payments recorded yet.", icon="💰")
    else:
        rows_html = ""
        for p in recent_payments:
            method_label = p["method"].replace("_", " ").title()
            pill = status_pill(method_label, "neutral")
            rows_html += (
                f'<div style="display:flex; justify-content:space-between; align-items:center; '
                f'padding:9px 0; border-bottom:1px solid {c["BORDER"]};">'
                f'<div>'
                f'<div style="font-size:13px; font-weight:500;">{p["guest_name"]}</div>'
                f'<div style="font-size:11px; color:{c["TEXT_MUTED"]};">{p["payment_date"]} · Unit {p["unit_number"]}</div>'
                f'</div>'
                f'<div style="text-align:right;">'
                f'<div style="font-size:13px; font-weight:600; color:{c["ACCENT_DARK"]};">{currency} {p["amount"]:,.0f}</div>'
                f'{pill}</div></div>'
            )
        st.markdown(
            f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
            f'border-radius:14px; padding:0.25rem 1.1rem;">{rows_html}</div>',
            unsafe_allow_html=True,
        )

st.divider()

with st.expander("ℹ️ What GuesthousePro does"):
    features = [
        ("🏢", "Units & Rooms",            "Manage all your apartments with live status."),
        ("📅", "Reservations & Calendar",  "Visual booking grid, check-in/out workflow."),
        ("👤", "Guest Profiles",           "Store contacts, IDs, stay history, preferences."),
        ("💰", "Billing & Payments",       "Folios, extra charges, MoMo, cash, bank, receipts."),
        ("🧹", "Housekeeping Board",       "Room status tracking — dirty, cleaning, inspected, ready."),
        ("🔧", "Maintenance",              "Log issues, assign staff, block rooms automatically."),
        ("💵", "Expenses",                 "Track operating costs for accurate profit reporting."),
        ("📲", "WhatsApp Messaging",       "Booking confirmations, reminders, and checkout messages."),
        ("📊", "Reports",                  "Occupancy, revenue, ADR, booking sources, expenses."),
    ]
    items_html = "".join(
        f'<div style="display:flex; align-items:flex-start; gap:10px; padding:7px 0; border-bottom:1px solid {c["BORDER"]};">'
        f'<span style="font-size:16px; line-height:1.4;">{icon}</span>'
        f'<div><span style="font-size:13px; font-weight:600; color:{c["BRAND_TEXT"]};">{title}</span>'
        f'<span style="font-size:12px; color:{c["TEXT_MUTED"]};">&nbsp;&mdash; {desc}</span></div></div>'
        for icon, title, desc in features
    )
    st.markdown(
        f'<p style="font-size:13px; color:{c["TEXT_MUTED"]}; line-height:1.55; margin-bottom:10px;">'
        f'GuesthousePro is a smart, all-in-one Property Management System built for guesthouses, '
        f'serviced apartments, and short-stay properties in Africa (and anywhere else). '
        f'Manage every room, guest, and booking from one place &mdash; no notebooks, no spreadsheets.</p>'
        f'{items_html}'
        f'<p style="margin:10px 0 0; font-size:12px; color:{c["TEXT_MUTED"]}; font-style:italic;">'
        f'First month free &middot; No setup fee &middot; Works on any device</p>',
        unsafe_allow_html=True,
    )

st.caption("GuesthousePro · Use the sidebar to manage units, reservations, guests, billing, housekeeping, maintenance, expenses, messages, reports and settings.")
