"""
Dedicated Check-in / Check-out page.
A focused, no-distraction workflow for reception staff.
"""
import streamlit as st
from datetime import date
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.logic import (
    list_reservations, get_reservation, check_in_reservation,
    check_out_reservation, folio_summary, record_payment,
)
from utils.whatsapp import (
    build_booking_confirmation, build_checkout_reminder,
    build_post_checkout_message, whatsapp_link, log_message,
)
from utils.theme import (
from utils.i18n import t
    apply_theme, page_header, empty_state, section_label,
    subscription_banner, require_active_subscription, status_pill, colors, metric_row,
)

st.set_page_config(page_title="Check In / Out", page_icon="🛎️", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
account    = get_account(account_id) or {}
currency   = account.get("currency", "UGX")
c = colors()

page_header("Check In / Check Out", subtitle="Arrival · Departure · Quick payment at desk", icon="🛎️")
subscription_banner()
st.write("")

tab1, tab2 = st.tabs(["🛬 Arrivals / Check In", "🛫 In-House / Check Out"])

# ── Tab 1: Arrivals ────────────────────────────────────────────────────────────
with tab1:
    today = date.today().isoformat()
    pending = list_reservations(account_id=account_id, status="reserved")

    # Highlight arrivals today vs future
    arriving_today  = [r for r in pending if r["check_in_date"] == today]
    arriving_future = [r for r in pending if r["check_in_date"] > today]

    if not pending:
        empty_state("No pending reservations.", icon="🛬")
    else:
        if arriving_today:
            st.markdown(
                f'<div style="background:{c["SUCCESS_SOFT"]}; border:1px solid {c["BORDER"]}; '
                f'border-radius:12px; padding:0.75rem 1rem; margin-bottom:1rem;">'
                f'<strong>🛬 {len(arriving_today)} arrival(s) expected today ({today})</strong>'
                f'</div>',
                unsafe_allow_html=True,
            )

        section_label("Today's arrivals" if arriving_today else "No arrivals today")
        for r in arriving_today:
            folio = folio_summary(r["id"])
            with st.expander(f"🛬 {r['guest_name']} · Unit {r['unit_number']} ({r['unit_type']}) · {r['check_in_date']}"):
                col1, col2 = st.columns(2)
                col1.write(f"**Booking:** {r['booking_ref']}")
                col1.write(f"**Check-out:** {r['check_out_date']}")
                col1.write(f"**Nights:** {r['num_nights']}")
                col1.write(f"**Guests:** {r['num_guests']}")
                col1.write(f"**Source:** {r['booking_source']}")
                col2.write(f"**Rate/night:** {currency} {r['rate_per_night']:,.0f}")
                col2.write(f"**Accommodation:** {currency} {r['accommodation_total']:,.0f}")
                col2.write(f"**Paid so far:** {currency} {folio['paid']:,.0f}")
                if folio["balance"] > 0:
                    col2.error(f"Balance to collect: {currency} {folio['balance']:,.0f}")
                else:
                    col2.success("Fully paid ✓")
                if r.get("special_requests"):
                    st.info(f"Special requests: {r['special_requests']}")

                # Quick deposit collection before check-in
                if folio["balance"] > 0:
                    st.markdown("**Collect payment at check-in:**")
                    with st.form(f"ci_payment_{r['id']}"):
                        pa1, pa2 = st.columns(2)
                        ci_amount = pa1.number_input(
                            f"Amount ({currency})", min_value=0.0,
                            value=float(folio["balance"]), step=10000.0,
                        )
                        ci_method = pa2.selectbox("Method", ["cash", "mobile_money", "bank", "card", "other"])
                        ci_ref = ""
                        if ci_method == "mobile_money":
                            ci_ref = st.text_input("MoMo reference", key=f"ci_mref_{r['id']}")
                        ci_pay = st.form_submit_button("Record payment + Check In", type="primary")
                        if ci_pay:
                            if not require_active_subscription(): pass
                            elif ci_amount > 0:
                                record_payment(r["id"], ci_amount, today, ci_method, ci_ref, "", "accommodation", "Collected at check-in")
                            check_in_reservation(r["id"])
                            st.success(f"✅ {r['guest_name']} checked in to Unit {r['unit_number']}!")
                            if r.get("guest_phone"):
                                msg  = build_booking_confirmation(r["id"])
                                link = whatsapp_link(r["guest_phone"], msg)
                                st.markdown(
                                    f'<a href="{link}" target="_blank" style="display:inline-flex; align-items:center; gap:6px; '
                                    f'background:#25D366; color:#fff; text-decoration:none; font-size:12px; font-weight:600; '
                                    f'padding:7px 16px; border-radius:8px;">📲 Send welcome WhatsApp</a>',
                                    unsafe_allow_html=True,
                                )
                            st.rerun()
                else:
                    if st.button(f"✅ CHECK IN — {r['guest_name']}", key=f"ci_nobill_{r['id']}", type="primary"):
                        if require_active_subscription():
                            check_in_reservation(r["id"])
                            st.success(f"✅ {r['guest_name']} checked in to Unit {r['unit_number']}!")
                            st.rerun()

        if arriving_future:
            st.write("")
            section_label(f"Upcoming arrivals ({len(arriving_future)})")
            for r in arriving_future:
                folio = folio_summary(r["id"])
                st.markdown(
                    f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
                    f'border-radius:10px; padding:0.65rem 1rem; margin-bottom:0.4rem; '
                    f'display:flex; justify-content:space-between; align-items:center;">'
                    f'<div>'
                    f'<span style="font-size:13px; font-weight:500;">{r["guest_name"]}</span> '
                    f'<span style="font-size:12px; color:{c["TEXT_MUTED"]};">· Unit {r["unit_number"]} · {r["check_in_date"]} → {r["check_out_date"]}</span>'
                    f'</div>'
                    f'<span style="font-size:12px; color:{c["TEXT_MUTED"]};">{r["booking_ref"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

# ── Tab 2: In-house / check-out ────────────────────────────────────────────────
with tab2:
    today = date.today().isoformat()
    in_house = list_reservations(account_id=account_id, status="checked_in")

    if not in_house:
        empty_state("No guests currently checked in.", icon="🛫")
    else:
        due_today = [r for r in in_house if r["check_out_date"] == today]
        staying   = [r for r in in_house if r["check_out_date"] > today]
        overdue   = [r for r in in_house if r["check_out_date"] < today]

        if overdue:
            st.error(f"⚠️ {len(overdue)} guest(s) past their scheduled checkout date!")

        metric_row([
            {"label": "Guests in house",    "value": str(len(in_house)),  "tone": "accent"},
            {"label": "Due out today",       "value": str(len(due_today)), "tone": "warning"},
            {"label": "Staying on",          "value": str(len(staying)),   "tone": "neutral"},
            {"label": "Overdue checkout",    "value": str(len(overdue)),   "tone": "danger"},
        ])

        if overdue:
            section_label("⚠️ Overdue checkouts")
            for r in overdue:
                folio = folio_summary(r["id"])
                with st.expander(f"❗ {r['guest_name']} · Unit {r['unit_number']} · Was due {r['check_out_date']}"):
                    st.error(f"Guest was due to check out on {r['check_out_date']}")
                    if folio["balance"] > 0:
                        st.warning(f"Outstanding balance: {currency} {folio['balance']:,.0f}")
                    if st.button(f"🛫 Check Out Now — {r['guest_name']}", key=f"co_ov_{r['id']}", type="primary"):
                        if require_active_subscription():
                            check_out_reservation(r["id"])
                            st.success(f"Checked out. Unit {r['unit_number']} sent to housekeeping.")
                            st.rerun()

        if due_today:
            section_label(f"🛫 Departures today ({len(due_today)})")
            for r in due_today:
                folio = folio_summary(r["id"])
                with st.expander(f"🛫 {r['guest_name']} · Unit {r['unit_number']} · Due out today"):
                    col1, col2 = st.columns(2)
                    col1.write(f"**Booking:** {r['booking_ref']}")
                    col1.write(f"**Checked in:** {r['check_in_date']}")
                    col1.write(f"**Nights:** {r['num_nights']}")
                    col2.write(f"**Total bill:** {currency} {folio['total']:,.0f}")
                    col2.write(f"**Paid:** {currency} {folio['paid']:,.0f}")
                    if folio["balance"] > 0:
                        col2.error(f"Balance owing: {currency} {folio['balance']:,.0f}")
                        # Quick payment at checkout
                        with st.form(f"co_payment_{r['id']}"):
                            co_amount = st.number_input(
                                f"Collect balance ({currency})", min_value=0.0,
                                value=float(folio["balance"]), step=10000.0,
                            )
                            co_method = st.selectbox("Method", ["cash", "mobile_money", "bank", "card", "other"])
                            co_ref = ""
                            if co_method == "mobile_money":
                                co_ref = st.text_input("MoMo reference", key=f"co_mref_{r['id']}")
                            co_btn = st.form_submit_button("Collect payment + Check Out", type="primary")
                            if co_btn:
                                if not require_active_subscription(): pass
                                elif co_amount > 0:
                                    record_payment(r["id"], co_amount, today, co_method, co_ref, "", "accommodation", "Collected at checkout")
                                check_out_reservation(r["id"])
                                st.success(f"✅ {r['guest_name']} checked out. Unit {r['unit_number']} → housekeeping.")
                                if r.get("guest_phone"):
                                    msg  = build_post_checkout_message(r["id"])
                                    link = whatsapp_link(r["guest_phone"], msg)
                                    st.markdown(
                                        f'<a href="{link}" target="_blank" style="display:inline-flex; align-items:center; gap:6px; '
                                        f'background:#25D366; color:#fff; text-decoration:none; font-size:12px; font-weight:600; '
                                        f'padding:7px 16px; border-radius:8px;">📲 Send thank-you WhatsApp</a>',
                                        unsafe_allow_html=True,
                                    )
                                st.rerun()
                    else:
                        col2.success("Fully settled ✓")
                        if st.button(f"🛫 CHECK OUT — {r['guest_name']}", key=f"co_settled_{r['id']}", type="primary"):
                            if require_active_subscription():
                                check_out_reservation(r["id"])
                                st.success(f"✅ Checked out. Unit {r['unit_number']} → housekeeping.")
                                st.rerun()

        if staying:
            section_label(f"🏠 Staying on ({len(staying)})")
            for r in staying:
                folio = folio_summary(r["id"])
                balance_tone = "danger" if folio["balance"] > 0 else "neutral"
                balance_pill = status_pill(
                    f"{currency} {folio['balance']:,.0f} owed" if folio["balance"] > 0 else "Settled",
                    balance_tone,
                )
                st.markdown(
                    f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
                    f'border-radius:10px; padding:0.65rem 1rem; margin-bottom:0.4rem;">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                    f'<div>'
                    f'<span style="font-size:13px; font-weight:500;">{r["guest_name"]}</span> '
                    f'<span style="font-size:12px; color:{c["TEXT_MUTED"]};">· Unit {r["unit_number"]} · checkout {r["check_out_date"]}</span>'
                    f'</div>'
                    f'{balance_pill}'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
