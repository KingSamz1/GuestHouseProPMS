import streamlit as st
from datetime import date, timedelta
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.logic import (
    list_units, list_guests, add_guest, create_reservation, list_reservations,
    get_reservation, check_in_reservation, check_out_reservation, cancel_reservation,
    unit_is_available, folio_summary, BOOKING_SOURCES,
)
from utils.theme import apply_theme, page_header, empty_state, section_label, subscription_banner, require_active_subscription, status_pill, colors
from utils.i18n import t

st.set_page_config(page_title="Reservations", page_icon="📅", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
account    = get_account(account_id) or {}
currency   = account.get("currency", "UGX")
c = colors()

page_header("Reservations & Bookings", subtitle="Calendar · Check-in · Check-out", icon="📅")
subscription_banner()
st.write("")

tab1, tab2, tab3, tab4 = st.tabs(["📋 All Bookings", "🗓️ Availability Grid", "➕ New Booking", "🛬 Check In/Out"])

# ── Tab 1: All bookings ────────────────────────────────────────────────────────
with tab1:
    status_filter = st.radio("Status", ["all", "reserved", "checked_in", "checked_out", "cancelled"], horizontal=True)
    resos = list_reservations(account_id=account_id, status=None if status_filter == "all" else status_filter)
    if not resos:
        empty_state("No reservations found.", icon="📅")
    else:
        for r in resos:
            folio = folio_summary(r["id"])
            balance_tone = "danger" if folio["balance"] > 0 else "success"
            balance_pill = status_pill(f"{currency} {folio['balance']:,.0f} {'owed' if folio['balance'] > 0 else 'settled'}", balance_tone)
            tone_map = {"reserved": "warning", "checked_in": "accent", "checked_out": "neutral", "cancelled": "danger"}
            status_p = status_pill(r["status"].replace("_", " ").title(), tone_map.get(r["status"], "neutral"))
            with st.expander(
                f"{r['booking_ref']} · {r['guest_name']} · Unit {r['unit_number']} · {r['check_in_date']} → {r['check_out_date']}"
            ):
                col1, col2, col3 = st.columns(3)
                col1.markdown(f"**Status:** {status_p}", unsafe_allow_html=True)
                col1.write(f"**Guest:** {r['guest_name']}")
                col1.write(f"**Phone:** {r['guest_phone'] or '—'}")
                col1.write(f"**Source:** {r['booking_source']}")
                col2.write(f"**Unit:** {r['unit_type']} — {r['unit_number']}")
                col2.write(f"**Check-in:** {r['check_in_date']}")
                col2.write(f"**Check-out:** {r['check_out_date']}")
                col2.write(f"**Nights:** {r['num_nights']} · Guests: {r['num_guests']}")
                col3.write(f"**Rate/night:** {currency} {r['rate_per_night']:,.0f}")
                col3.write(f"**Accommodation:** {currency} {r['accommodation_total']:,.0f}")
                col3.write(f"**Total (incl. extras):** {currency} {folio['total']:,.0f}")
                col3.markdown(f"**Balance:** {balance_pill}", unsafe_allow_html=True)
                if r["special_requests"]:
                    st.info(f"Special requests: {r['special_requests']}")
                if r["notes"]:
                    st.caption(f"Notes: {r['notes']}")

                if r["status"] == "reserved":
                    bcol1, bcol2 = st.columns(2)
                    if bcol1.button("✅ Check In", key=f"ci_{r['id']}"):
                        if require_active_subscription():
                            check_in_reservation(r["id"])
                            st.success(f"{r['guest_name']} checked in to Unit {r['unit_number']}.")
                            st.rerun()
                    if bcol2.button("❌ Cancel booking", key=f"cancel_{r['id']}"):
                        if require_active_subscription():
                            cancel_reservation(r["id"])
                            st.warning("Booking cancelled. Unit set to available.")
                            st.rerun()
                elif r["status"] == "checked_in":
                    if st.button("🛫 Check Out", key=f"co_{r['id']}", type="primary"):
                        if require_active_subscription():
                            check_out_reservation(r["id"])
                            st.success(f"{r['guest_name']} checked out from Unit {r['unit_number']}. Room marked for cleaning.")
                            st.rerun()

# ── Tab 2: Availability grid ──────────────────────────────────────────────────
with tab2:
    section_label("7-day availability grid")
    grid_start = st.date_input("From date", value=date.today())
    days_to_show = 7
    grid_end  = grid_start + timedelta(days=days_to_show - 1)
    units_all = list_units(account_id=account_id)
    resos_window = list_reservations(
        account_id=account_id,
        date_from=grid_start.isoformat(),
        date_to=(grid_end + timedelta(days=1)).isoformat(),
    )
    occupied_map = {}
    for r in resos_window:
        if r["status"] == "cancelled":
            continue
        ci = date.fromisoformat(r["check_in_date"])
        co = date.fromisoformat(r["check_out_date"])
        d  = ci
        while d < co:
            occupied_map[(r["unit_id"], d.isoformat())] = r["guest_name"][:8]
            d += timedelta(days=1)

    if not units_all:
        empty_state("No units added yet.", icon="🏘️")
    else:
        dates = [grid_start + timedelta(days=i) for i in range(days_to_show)]
        rows  = []
        for u in units_all:
            cells = []
            for d in dates:
                key = (u["id"], d.isoformat())
                if key in occupied_map:
                    cells.append(f"🟦 {occupied_map[key]}")
                elif u["status"] == "maintenance":
                    cells.append("🔧 Maint.")
                elif u["status"] in ("cleaning", "dirty"):
                    cells.append("🧹 Clean")
                else:
                    cells.append("✅ Free")
            label = f"{u['unit_number']} ({u['unit_type'][:6]})"
            rows.append({"Unit": label, **{d.strftime("%d %b"): cells[i] for i, d in enumerate(dates)}})
        import pandas as pd
        df = pd.DataFrame(rows).set_index("Unit")
        st.dataframe(df, use_container_width=True)
        st.caption("🟦 = occupied/reserved  ✅ = available  🧹 = cleaning  🔧 = maintenance")

# ── Tab 3: New booking — all live, no st.form wrapper ────────────────────────
with tab3:
    section_label("Create a new reservation")
    units_all  = list_units(account_id=account_id)
    guests_all = list_guests(account_id=account_id)

    if not units_all:
        empty_state("Add your rooms first on the Units page.", icon="🏘️")
    else:
        # ── Guest section ──────────────────────────────────────────────────────
        st.markdown("**👤 Guest**")
        guest_mode = st.radio(
            "guest_mode", ["Select existing guest", "Add new guest"],
            horizontal=True, label_visibility="collapsed",
            key="nb_guest_mode",
        )

        guest_id_selected = None

        if guest_mode == "Select existing guest":
            if guests_all:
                guest_options = {f"{g['full_name']} — {g['phone'] or 'no phone'}": g["id"] for g in guests_all}
                guest_label   = st.selectbox("Choose guest", list(guest_options.keys()), key="nb_guest_sel")
                guest_id_selected = guest_options[guest_label]
            else:
                st.info("No guests on file yet. Switch to 'Add new guest' to create one on the fly, or add them on the Guests page first.")
        else:
            ng_col1, ng_col2 = st.columns(2)
            with ng_col1:
                new_name  = st.text_input("Guest full name *", key="nb_new_name")
                new_phone = st.text_input("Phone", key="nb_new_phone")
            with ng_col2:
                new_nat   = st.text_input("Nationality", key="nb_new_nat")
                new_email = st.text_input("Email", key="nb_new_email")

        st.write("")
        # ── Unit & dates ───────────────────────────────────────────────────────
        st.markdown("**🏢 Room & Dates**")
        avail_units  = [u for u in units_all if u["status"] not in ("maintenance", "occupied")]
        show_units   = avail_units if avail_units else units_all
        unit_options = {
            f"Unit {u['unit_number']} — {u['unit_type']}  ({currency} {u['rate_nightly']:,.0f}/night)": u
            for u in show_units
        }
        if not avail_units:
            st.warning("No units are currently available. Showing all units.")

        unit_label    = st.selectbox("Room *", list(unit_options.keys()), key="nb_unit")
        selected_unit = unit_options[unit_label]

        dc1, dc2 = st.columns(2)
        with dc1:
            check_in  = st.date_input("Check-in date *", value=date.today(), key="nb_ci")
        with dc2:
            check_out = st.date_input("Check-out date *", value=date.today() + timedelta(days=1), key="nb_co")

        num_guests = st.number_input(
            "Number of guests", min_value=1, max_value=int(selected_unit["max_guests"]),
            value=1, step=1, key="nb_nguests",
        )

        st.write("")
        # ── Rate — live preview ────────────────────────────────────────────────
        st.markdown("**💰 Rate**")
        rate_type = st.selectbox("Rate type", ["nightly", "monthly", "custom"], key="nb_rate_type")

        if rate_type == "nightly":
            default_rate = float(selected_unit["rate_nightly"])
        elif rate_type == "monthly":
            default_rate = float(selected_unit["rate_monthly"] / 30) if selected_unit["rate_monthly"] else float(selected_unit["rate_nightly"])
        else:
            default_rate = float(selected_unit["rate_nightly"])

        rate_per_night = st.number_input(
            f"Rate per night ({currency}) *",
            min_value=0.0, value=default_rate, step=10000.0, key="nb_rate",
        )

        # Live total — updates instantly as user changes dates or rate
        if check_out > check_in:
            nights = (check_out - check_in).days
            total  = nights * rate_per_night
            st.info(f"**{nights} night(s) × {currency} {rate_per_night:,.0f} = {currency} {total:,.0f}**")
        else:
            st.warning("Check-out must be after check-in.")
            nights = 0

        st.write("")
        # ── Extra details ──────────────────────────────────────────────────────
        st.markdown("**📋 Details**")
        d1, d2 = st.columns(2)
        with d1:
            deposit_paid    = st.number_input(f"Deposit paid now ({currency})", min_value=0.0, step=10000.0, key="nb_deposit")
            booking_source  = st.selectbox("Booking source *", BOOKING_SOURCES, key="nb_source")
        with d2:
            special_requests = st.text_input("Special requests", key="nb_special")
            notes            = st.text_area("Internal notes", height=68, key="nb_notes")

        st.write("")
        can_submit = nights > 0

        if st.button("✅ Create reservation", type="primary", disabled=not can_submit):
            if not require_active_subscription():
                pass
            else:
                # Resolve / create guest
                gid = guest_id_selected
                if guest_mode == "Add new guest":
                    _name = st.session_state.get("nb_new_name", "").strip()
                    if not _name:
                        st.error("Guest name is required.")
                        st.stop()
                    gid = add_guest(
                        account_id, _name,
                        st.session_state.get("nb_new_phone", "").strip(),
                        st.session_state.get("nb_new_email", "").strip(),
                        st.session_state.get("nb_new_nat", "").strip(),
                    )

                if not gid:
                    st.error("Please select or add a guest.")
                elif not unit_is_available(selected_unit["id"], check_in.isoformat(), check_out.isoformat()):
                    st.error("This room already has a booking for those dates. Check the Availability Grid.")
                else:
                    res_id, ref = create_reservation(
                        account_id=account_id,
                        unit_id=selected_unit["id"],
                        guest_id=gid,
                        check_in_date=check_in.isoformat(),
                        check_out_date=check_out.isoformat(),
                        num_guests=int(num_guests),
                        rate_type=rate_type,
                        rate_per_night=rate_per_night,
                        booking_source=booking_source,
                        deposit_paid=deposit_paid,
                        special_requests=special_requests.strip(),
                        notes=notes.strip(),
                    )
                    st.success(f"✅ Reservation **{ref}** created! Unit {selected_unit['unit_number']} is now reserved.")
                    st.balloons()
                    st.rerun()

# ── Tab 4: Quick check-in / check-out ────────────────────────────────────────
with tab4:
    section_label("Quick check-in")
    pending = list_reservations(account_id=account_id, status="reserved")
    if not pending:
        empty_state("No pending reservations awaiting check-in.", icon="🛬")
    else:
        for r in pending:
            folio = folio_summary(r["id"])
            with st.expander(f"🛬 {r['guest_name']} · Unit {r['unit_number']} · Arriving {r['check_in_date']}"):
                col1, col2 = st.columns(2)
                col1.write(f"**Booking:** {r['booking_ref']}")
                col1.write(f"**Check-out:** {r['check_out_date']}")
                col1.write(f"**Nights:** {r['num_nights']}")
                col2.write(f"**Total:** {currency} {folio['total']:,.0f}")
                col2.write(f"**Paid:** {currency} {folio['paid']:,.0f}")
                col2.write(f"**Balance:** {currency} {folio['balance']:,.0f}")
                if st.button(f"✅ CHECK IN — {r['guest_name']}", key=f"qci_{r['id']}", type="primary"):
                    if require_active_subscription():
                        check_in_reservation(r["id"])
                        st.success(f"Checked in! Unit {r['unit_number']} is now occupied.")
                        st.rerun()

    st.divider()
    section_label("Quick check-out")
    in_house = list_reservations(account_id=account_id, status="checked_in")
    if not in_house:
        empty_state("No guests currently checked in.", icon="🛫")
    else:
        for r in in_house:
            folio = folio_summary(r["id"])
            with st.expander(f"🛫 {r['guest_name']} · Unit {r['unit_number']} · Due out {r['check_out_date']}"):
                col1, col2 = st.columns(2)
                col1.write(f"**Booking:** {r['booking_ref']}")
                col1.write(f"**Checked in:** {r['check_in_date']}")
                col2.write(f"**Total bill:** {currency} {folio['total']:,.0f}")
                col2.write(f"**Paid:** {currency} {folio['paid']:,.0f}")
                if folio["balance"] > 0:
                    col2.error(f"Balance owing: {currency} {folio['balance']:,.0f}")
                else:
                    col2.success("Fully settled ✓")
                if st.button(f"🛫 CHECK OUT — {r['guest_name']}", key=f"qco_{r['id']}", type="primary"):
                    if require_active_subscription():
                        check_out_reservation(r["id"])
                        st.success(f"Checked out. Unit {r['unit_number']} sent to housekeeping.")
                        st.rerun()
