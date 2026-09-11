import streamlit as st
from datetime import date
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.logic import (
    list_reservations, get_reservation, folio_summary,
    add_folio_item, list_folio_items, delete_folio_item,
    record_payment, list_payments, get_payment,
)
from utils.receipts import generate_receipt, get_receipt_for_payment, REPORTLAB_AVAILABLE
from utils.whatsapp import build_balance_reminder, whatsapp_link, log_message
from utils.theme import (
    apply_theme, page_header, empty_state, section_label,
    subscription_banner, require_active_subscription, status_pill, colors,
)

st.set_page_config(page_title="Billing", page_icon="💰", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
account    = get_account(account_id) or {}
currency   = account.get("currency", "UGX")
c = colors()

PAYMENT_METHODS = ["cash", "mobile_money", "bank", "card", "other"]
MOMO_PROVIDERS  = ["MTN Mobile Money", "Airtel Money", "Other"]
EXTRA_SERVICES  = [
    "Airport Transfer", "Laundry", "Extra Cleaning", "Breakfast",
    "Dinner", "Parking", "Early Check-in", "Late Check-out",
    "Extra Bed", "Minibar", "Wi-Fi Upgrade", "Other",
]

page_header("Billing & Payments", subtitle="Guest folios · Extra charges · Payments · Receipts", icon="💰")
subscription_banner()
st.write("")

tab1, tab2, tab3 = st.tabs(["📑 Guest Folio", "💳 Record Payment", "📋 Payment History"])

# ── Tab 1: Guest folio ─────────────────────────────────────────────────────────
with tab1:
    active = list_reservations(account_id=account_id)
    active = [r for r in active if r["status"] in ("reserved", "checked_in")]
    if not active:
        empty_state("No active reservations. Check-in a guest first.", icon="💰")
    else:
        folio_options = {
            f"{r['booking_ref']} · {r['guest_name']} · Unit {r['unit_number']} · {r['check_in_date']}": r["id"]
            for r in active
        }
        selected_label = st.selectbox("Select active reservation", list(folio_options.keys()))
        res_id = folio_options[selected_label]
        res    = get_reservation(res_id)
        folio  = folio_summary(res_id)
        items  = list_folio_items(res_id)

        st.write("")
        # Folio header card
        prop = account.get("property_name", "Property")
        st.markdown(
            f'<div style="background:{c["ACCENT_SOFT"]}; border:1px solid {c["BORDER"]}; '
            f'border-radius:14px; padding:1.1rem 1.4rem; margin-bottom:1rem;">'
            f'<div style="font-size:15px; font-weight:700; color:{c["BRAND_TEXT"]}; margin-bottom:4px;">'
            f'📑 {prop} — Guest Folio</div>'
            f'<div style="font-size:13px; color:{c["TEXT_MUTED"]};">'
            f'<strong>{res["guest_name"]}</strong> &nbsp;·&nbsp; Unit {res["unit_number"]} ({res["unit_type"]}) &nbsp;·&nbsp; '
            f'{res["check_in_date"]} → {res["check_out_date"]} &nbsp;·&nbsp; Ref: {res["booking_ref"]}'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # Line items
        section_label("Charges")
        rows_html = (
            f'<div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid {c["BORDER"]};">'
            f'<span style="font-size:13px;">🏠 Accommodation ({res["num_nights"]} night(s) × {currency} {res["rate_per_night"]:,.0f})</span>'
            f'<span style="font-size:13px; font-weight:600;">{currency} {res["accommodation_total"]:,.0f}</span>'
            f'</div>'
        )
        for item in items:
            rows_html += (
                f'<div style="display:flex; justify-content:space-between; align-items:center; '
                f'padding:7px 0; border-bottom:1px solid {c["BORDER"]};">'
                f'<span style="font-size:13px;">➕ {item["description"]}</span>'
                f'<div style="display:flex; align-items:center; gap:10px;">'
                f'<span style="font-size:13px; font-weight:600;">{currency} {item["amount"]:,.0f}</span>'
                f'</div></div>'
            )
        total_line = (
            f'<div style="display:flex; justify-content:space-between; padding:10px 0; margin-top:4px;">'
            f'<span style="font-size:15px; font-weight:700;">TOTAL</span>'
            f'<span style="font-size:15px; font-weight:700; color:{c["ACCENT_DARK"]};">{currency} {folio["total"]:,.0f}</span>'
            f'</div>'
            f'<div style="display:flex; justify-content:space-between; padding:4px 0;">'
            f'<span style="font-size:13px; color:{c["TEXT_MUTED"]};">Paid</span>'
            f'<span style="font-size:13px; color:{c["SUCCESS"]};">{currency} {folio["paid"]:,.0f}</span>'
            f'</div>'
        )
        balance_color = c["DANGER"] if folio["balance"] > 0 else c["SUCCESS"]
        balance_label = "BALANCE OWING" if folio["balance"] > 0 else "SETTLED ✓"
        balance_line = (
            f'<div style="display:flex; justify-content:space-between; padding:8px 0; '
            f'border-top:2px solid {c["BORDER"]}; margin-top:6px;">'
            f'<span style="font-size:14px; font-weight:700; color:{balance_color};">{balance_label}</span>'
            f'<span style="font-size:14px; font-weight:700; color:{balance_color};">{currency} {folio["balance"]:,.0f}</span>'
            f'</div>'
        )
        st.markdown(
            f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
            f'border-radius:14px; padding:0.5rem 1.2rem;">'
            f'{rows_html}{total_line}{balance_line}</div>',
            unsafe_allow_html=True,
        )

        # Delete extra charges
        if items:
            st.write("")
            section_label("Remove an extra charge")
            item_options = {f"{i['description']} — {currency} {i['amount']:,.0f}": i["id"] for i in items}
            del_label = st.selectbox("Select charge to remove", list(item_options.keys()), key="del_folio_item")
            if st.button("🗑️ Remove charge", key="rm_folio"):
                if require_active_subscription():
                    delete_folio_item(item_options[del_label])
                    st.success("Charge removed.")
                    st.rerun()

        st.divider()
        section_label("Add extra charge")
        with st.form("add_folio_form", clear_on_submit=True):
            fc1, fc2 = st.columns(2)
            with fc1:
                svc = st.selectbox("Service type", EXTRA_SERVICES)
                custom_desc = st.text_input("Custom description (optional)")
            with fc2:
                extra_amount = st.number_input(f"Amount ({currency})", min_value=0.0, step=5000.0)
            add_charge = st.form_submit_button("Add charge to folio", type="primary")
            if add_charge:
                if not require_active_subscription(): pass
                elif extra_amount <= 0:
                    st.error("Amount must be greater than zero.")
                else:
                    desc = custom_desc.strip() if custom_desc.strip() else svc
                    add_folio_item(res_id, desc, extra_amount)
                    st.success(f"Added: {desc} — {currency} {extra_amount:,.0f}")
                    st.rerun()

        # WhatsApp balance reminder
        if folio["balance"] > 0 and res.get("guest_phone"):
            st.divider()
            section_label("Send balance reminder via WhatsApp")
            msg = build_balance_reminder(res_id, folio["balance"], currency)
            st.text_area("Message preview", value=msg, height=90, disabled=True)
            link = whatsapp_link(res["guest_phone"], msg)
            st.markdown(
                f'<a href="{link}" target="_blank" style="display:inline-flex; align-items:center; gap:8px; '
                f'background:#25D366; color:#fff; text-decoration:none; font-size:13px; font-weight:600; '
                f'padding:9px 20px; border-radius:9px;">📲 Open in WhatsApp</a>',
                unsafe_allow_html=True,
            )
            if st.button("Log as sent", key="log_bal"):
                log_message(res_id, "balance_reminder", msg)
                st.success("Logged.")

# ── Tab 2: Record payment ──────────────────────────────────────────────────────
with tab2:
    all_open = list_reservations(account_id=account_id)
    all_open = [r for r in all_open if r["status"] in ("reserved", "checked_in")]
    if not all_open:
        empty_state("No active reservations to record payment against.", icon="💳")
    else:
        pay_options = {
            f"{r['booking_ref']} · {r['guest_name']} · Unit {r['unit_number']}": r["id"]
            for r in all_open
        }
        pay_label = st.selectbox("Select reservation", list(pay_options.keys()), key="pay_res_sel")
        pay_res_id = pay_options[pay_label]
        pay_folio  = folio_summary(pay_res_id)

        bc1, bc2, bc3 = st.columns(3)
        bc1.metric("Total Bill",   f"{currency} {pay_folio['total']:,.0f}")
        bc2.metric("Already Paid", f"{currency} {pay_folio['paid']:,.0f}")
        bc3.metric("Balance",      f"{currency} {pay_folio['balance']:,.0f}")

        with st.form("record_payment_form", clear_on_submit=True):
            p_amount = st.number_input(
                f"Amount received ({currency})*",
                min_value=0.0,
                value=max(0.0, float(pay_folio["balance"])),
                step=10000.0,
            )
            p_date   = st.date_input("Payment date*", value=date.today())
            p_method = st.selectbox("Payment method*", PAYMENT_METHODS)
            p_momo_ref = p_momo_prov = ""
            if p_method == "mobile_money":
                mp1, mp2 = st.columns(2)
                with mp1:
                    p_momo_prov = st.selectbox("MoMo provider", MOMO_PROVIDERS)
                with mp2:
                    p_momo_ref  = st.text_input("Transaction reference")
            p_type = st.selectbox("Payment type", ["accommodation", "deposit", "extras", "other"])
            p_note = st.text_input("Note (optional)")
            pay_sub = st.form_submit_button("Record payment", type="primary")
            if pay_sub:
                if not require_active_subscription(): pass
                elif p_amount <= 0:
                    st.error("Amount must be greater than zero.")
                else:
                    pay_id = record_payment(
                        pay_res_id, p_amount, p_date.isoformat(),
                        p_method, p_momo_ref, p_momo_prov, p_type, p_note,
                    )
                    st.success(f"Payment of {currency} {p_amount:,.0f} recorded.")

                    # Auto-generate receipt
                    if REPORTLAB_AVAILABLE:
                        try:
                            pr = get_receipt_for_payment(pay_id)
                            if not pr:
                                pay_data = get_payment(pay_id)
                                guest_name = pay_data["full_name"] if pay_data else ""
                                pr = generate_receipt(pay_id, display_name=guest_name)
                            with open(pr["file_path"], "rb") as rf:
                                st.download_button(
                                    f"📄 Download Receipt {pr['receipt_number']}",
                                    rf, file_name=pr["download_name"],
                                    mime="application/pdf", key=f"rcpt_{pay_id}",
                                )
                        except Exception as e:
                            st.warning(f"Could not generate receipt PDF: {e}")
                    st.rerun()

# ── Tab 3: Payment history ────────────────────────────────────────────────────
with tab3:
    all_payments = list_payments(account_id=account_id)
    if not all_payments:
        empty_state("No payments recorded yet.", icon="📋")
    else:
        st.caption(f"{len(all_payments)} payment(s) total")
        for p in all_payments:
            method_label = p["method"].replace("_", " ").title()
            pill = status_pill(method_label, "neutral")
            with st.expander(
                f"{p['payment_date']} · {p['guest_name']} · Unit {p['unit_number']} · {currency} {p['amount']:,.0f}"
            ):
                col1, col2 = st.columns(2)
                col1.write(f"**Booking ref:** {p['booking_ref']}")
                col1.write(f"**Guest:** {p['guest_name']}")
                col1.write(f"**Unit:** {p['unit_number']}")
                col2.write(f"**Amount:** {currency} {p['amount']:,.0f}")
                col2.markdown(f"**Method:** {pill}", unsafe_allow_html=True)
                col2.write(f"**Type:** {p['payment_type'].replace('_',' ').title()}")
                if p.get("momo_reference"):
                    col1.write(f"**MoMo ref:** {p['momo_reference']}")
                if p.get("momo_provider"):
                    col1.write(f"**Provider:** {p['momo_provider']}")
                if p.get("note"):
                    st.caption(f"Note: {p['note']}")

                # Receipt
                existing_receipt = get_receipt_for_payment(p["id"])
                if existing_receipt:
                    with open(existing_receipt["file_path"], "rb") as rf:
                        st.download_button(
                            f"📄 {existing_receipt['receipt_number']}",
                            rf, file_name=existing_receipt["download_name"],
                            mime="application/pdf", key=f"dl_rcpt_{p['id']}",
                        )
                elif REPORTLAB_AVAILABLE:
                    if st.button("Generate receipt", key=f"gen_rcpt_{p['id']}"):
                        try:
                            pr = generate_receipt(p["id"], display_name=p["full_name"])
                            with open(pr["file_path"], "rb") as rf:
                                st.download_button(
                                    f"📄 {pr['receipt_number']}",
                                    rf, file_name=pr["download_name"],
                                    mime="application/pdf", key=f"dl2_rcpt_{p['id']}",
                                )
                        except Exception as e:
                            st.error(f"Receipt error: {e}")
