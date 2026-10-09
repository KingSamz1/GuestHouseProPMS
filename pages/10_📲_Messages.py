import streamlit as st
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.logic import list_reservations, get_reservation
from utils.whatsapp import (
    build_booking_confirmation, build_arrival_reminder,
    build_checkout_reminder, build_post_checkout_message,
    whatsapp_link, log_message,
)
from utils.theme import (
from utils.i18n import t
    apply_theme, page_header, empty_state, section_label,
    subscription_banner, require_active_subscription, colors,
)

st.set_page_config(page_title="Messages", page_icon="📲", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
c = colors()

page_header("WhatsApp Guest Messages", subtitle="Confirmations · Reminders · Post-checkout · Custom", icon="📲")
subscription_banner()
st.write("")

MESSAGE_TYPES = {
    "Booking Confirmation":    ("confirmation",        build_booking_confirmation),
    "Arrival Reminder":        ("arrival_reminder",    build_arrival_reminder),
    "Checkout Reminder":       ("checkout_reminder",   build_checkout_reminder),
    "Post-checkout Thank You": ("post_checkout",       build_post_checkout_message),
}

all_resos = list_reservations(account_id=account_id)
active_resos = [r for r in all_resos if r["status"] not in ("cancelled",)]

if not active_resos:
    empty_state("No reservations yet. Create a booking first.", icon="📲")
    st.stop()

tab1, tab2 = st.tabs(["📨 Send Message", "📋 Message Log"])

with tab1:
    res_options = {
        f"{r['booking_ref']} · {r['guest_name']} · Unit {r['unit_number']} · {r['check_in_date']}": r["id"]
        for r in active_resos
    }
    selected_label = st.selectbox("Select reservation", list(res_options.keys()))
    res_id = res_options[selected_label]
    res    = get_reservation(res_id)

    if not res:
        st.error("Reservation not found.")
        st.stop()

    phone = res.get("guest_phone") or res.get("guest_phone", "")

    section_label("Guest contact")
    col1, col2 = st.columns(2)
    col1.write(f"**Guest:** {res['guest_name']}")
    col1.write(f"**Phone:** {phone or '—'}")
    col2.write(f"**Unit:** {res['unit_number']} ({res['unit_type']})")
    col2.write(f"**Stay:** {res['check_in_date']} → {res['check_out_date']}")

    if not phone:
        st.warning("No phone number on file for this guest. Add a phone number on the Guests page.")

    st.divider()
    section_label("Choose message type")
    msg_type_label = st.radio("Message type", list(MESSAGE_TYPES.keys()), horizontal=True)
    msg_type_key, builder_fn = MESSAGE_TYPES[msg_type_label]
    message_text = builder_fn(res_id)

    # Allow editing before sending
    edited_msg = st.text_area("Message (you can edit before sending)", value=message_text, height=140)

    if phone:
        wa_link = whatsapp_link(phone, edited_msg)
        st.markdown(
            f'<a href="{wa_link}" target="_blank" style="display:inline-flex; align-items:center; gap:8px; '
            f'background:#25D366; color:#fff; text-decoration:none; font-size:14px; font-weight:600; '
            f'padding:10px 22px; border-radius:9px; margin-top:8px;">📲 Open in WhatsApp</a>',
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button("✅ Mark as sent (log this message)"):
            log_message(res_id, msg_type_key, edited_msg)
            st.success("Message logged.")
    else:
        st.info("Enter a phone number for this guest to enable WhatsApp sending.")

    st.divider()
    section_label("Custom message")
    custom_phone = st.text_input("Send to phone number", value=phone or "", placeholder="+256701234567")
    custom_msg   = st.text_area("Custom message", height=120, placeholder="Type your custom message here…")
    if custom_phone.strip() and custom_msg.strip():
        custom_link = whatsapp_link(custom_phone.strip(), custom_msg.strip())
        st.markdown(
            f'<a href="{custom_link}" target="_blank" style="display:inline-flex; align-items:center; gap:8px; '
            f'background:#25D366; color:#fff; text-decoration:none; font-size:13px; font-weight:600; '
            f'padding:9px 20px; border-radius:9px;">📲 Send Custom Message</a>',
            unsafe_allow_html=True,
        )

with tab2:
    from utils.db import get_conn
    from utils.pg import fetchall
    with get_conn() as conn:
        logs = fetchall(conn,
            """SELECT ml.*, r.booking_ref, g.full_name
               FROM messages_log ml
               JOIN reservations r ON r.id = ml.reservation_id
               JOIN guests g ON g.id = r.guest_id
               WHERE r.account_id = %s
               ORDER BY ml.created_at DESC
               LIMIT 50""",
            (account_id,),
        )

    if not logs:
        empty_state("No messages logged yet.", icon="📋")
    else:
        st.caption(f"{len(logs)} message(s) logged")
        for log in logs:
            with st.expander(
                f"{log['created_at'][:16]} · {log['full_name']} · {log['message_type'].replace('_',' ').title()}"
            ):
                st.write(f"**Booking:** {log['booking_ref']}")
                st.write(f"**Type:** {log['message_type'].replace('_',' ').title()}")
                st.text_area("Message", value=log["message"], height=100, disabled=True, key=f"log_{log['id']}")
