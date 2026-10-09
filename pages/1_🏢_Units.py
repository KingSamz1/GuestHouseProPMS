import streamlit as st
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.logic import (
    add_unit, list_units, get_unit, update_unit, delete_unit, update_unit_status,
    UNIT_TYPES, UNIT_STATUSES,
)
from utils.theme import apply_theme, page_header, empty_state, section_label, subscription_banner, require_active_subscription, status_pill, unit_status_tone, colors, metric_row
from utils.i18n import t

st.set_page_config(page_title="Units", page_icon="🏢", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
account    = get_account(account_id) or {}
currency   = account.get("currency", "UGX")
c = colors()

page_header("Units & Rooms", subtitle="Manage your apartments and their live status", icon="🏢")
subscription_banner()
st.write("")

tab1, tab2, tab3 = st.tabs(["📋 All Units", "➕ Add Unit", "✏️ Edit / Delete"])

with tab1:
    units = list_units(account_id=account_id)
    if not units:
        empty_state("No units yet. Add your rooms in the 'Add Unit' tab.", icon="🏘️")
    else:
        # Status overview cards
        from collections import Counter
        status_counts = Counter(u["status"] for u in units)
        cols = st.columns(len(UNIT_STATUSES))
        for i, s in enumerate(UNIT_STATUSES):
            cnt = status_counts.get(s, 0)
            cols[i].metric(s.title(), cnt)

        st.write("")
        section_label("Unit status board")
        for u in units:
            tone = unit_status_tone(u["status"])
            pill = status_pill(u["status"].title(), tone)
            maint = f" · ⚠️ {u['maintenance_status']}" if u["maintenance_status"] != "ok" else ""
            with st.expander(f"Unit {u['unit_number']} — {u['unit_type']} · Floor {u['floor']}{maint}"):
                col1, col2, col3 = st.columns(3)
                col1.markdown(f"**Status:** {pill}", unsafe_allow_html=True)
                col1.write(f"**Type:** {u['unit_type']}")
                col1.write(f"**Floor:** {u['floor']}")
                col1.write(f"**Max guests:** {u['max_guests']}")
                col2.write(f"**Nightly rate:** {currency} {u['rate_nightly']:,.0f}")
                col2.write(f"**Weekend rate:** {currency} {u['rate_weekend']:,.0f}")
                col2.write(f"**Monthly rate:** {currency} {u['rate_monthly']:,.0f}")
                col3.write(f"**Amenities:** {u['amenities'] or '—'}")
                col3.write(f"**Notes:** {u['notes'] or '—'}")

                st.markdown("**Update status manually:**")
                new_status = st.selectbox(
                    "Set status", UNIT_STATUSES,
                    index=UNIT_STATUSES.index(u["status"]) if u["status"] in UNIT_STATUSES else 0,
                    key=f"status_sel_{u['id']}",
                )
                if st.button("Update status", key=f"upd_status_{u['id']}"):
                    if require_active_subscription():
                        update_unit_status(u["id"], new_status)
                        st.success(f"Unit {u['unit_number']} status updated to {new_status}.")
                        st.rerun()

with tab2:
    section_label("Add a new unit")
    with st.form("add_unit_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            unit_number = st.text_input("Unit number / name* (e.g. A01, 101)")
            unit_type   = st.selectbox("Unit type*", UNIT_TYPES)
            floor       = st.number_input("Floor", min_value=0, max_value=50, value=1, step=1)
            max_guests  = st.number_input("Max guests", min_value=1, max_value=20, value=2, step=1)
        with col2:
            rate_nightly = st.number_input(f"Nightly rate ({currency})*", min_value=0.0, step=10000.0)
            rate_weekend = st.number_input(f"Weekend rate ({currency})", min_value=0.0, step=10000.0)
            rate_monthly = st.number_input(f"Monthly rate ({currency})", min_value=0.0, step=50000.0)
        amenities = st.text_input("Amenities (comma-separated)", placeholder="TV, Wi-Fi, Fridge, Cooker, AC")
        notes     = st.text_area("Notes", height=60)
        submitted = st.form_submit_button("Add unit", type="primary")
        if submitted:
            if not require_active_subscription():
                pass
            elif not unit_number.strip():
                st.error("Unit number is required.")
            else:
                add_unit(account_id, unit_number.strip(), unit_type, int(floor), int(max_guests),
                         rate_nightly, rate_weekend, rate_monthly, amenities.strip(), notes.strip())
                st.success(f"Unit {unit_number} added.")
                st.rerun()

with tab3:
    units = list_units(account_id=account_id)
    if not units:
        empty_state("No units yet.", icon="🏘️")
    else:
        unit_options = {f"Unit {u['unit_number']} — {u['unit_type']}": u["id"] for u in units}
        selected_label = st.selectbox("Select unit to edit or delete", list(unit_options.keys()))
        selected_id    = unit_options[selected_label]
        u = get_unit(selected_id)

        if u:
            section_label("Edit unit")
            with st.form("edit_unit_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_number   = st.text_input("Unit number", value=u["unit_number"])
                    new_type     = st.selectbox("Unit type", UNIT_TYPES, index=UNIT_TYPES.index(u["unit_type"]) if u["unit_type"] in UNIT_TYPES else 0)
                    new_floor    = st.number_input("Floor", min_value=0, max_value=50, value=int(u["floor"]), step=1)
                    new_max      = st.number_input("Max guests", min_value=1, value=int(u["max_guests"]), step=1)
                with col2:
                    new_nightly  = st.number_input(f"Nightly rate ({currency})", min_value=0.0, value=float(u["rate_nightly"]), step=10000.0)
                    new_weekend  = st.number_input(f"Weekend rate ({currency})", min_value=0.0, value=float(u["rate_weekend"]), step=10000.0)
                    new_monthly  = st.number_input(f"Monthly rate ({currency})", min_value=0.0, value=float(u["rate_monthly"]), step=50000.0)
                new_amenities = st.text_input("Amenities", value=u["amenities"])
                new_notes     = st.text_area("Notes", value=u["notes"], height=60)
                save = st.form_submit_button("Save changes", type="primary")
                if save:
                    if not require_active_subscription():
                        pass
                    elif not new_number.strip():
                        st.error("Unit number is required.")
                    else:
                        update_unit(selected_id, new_number.strip(), new_type, int(new_floor), int(new_max),
                                    new_nightly, new_weekend, new_monthly, new_amenities.strip(), new_notes.strip())
                        st.success("Unit updated.")
                        st.rerun()

            st.write("")
            section_label("Danger zone")
            st.warning("Deleting a unit will also delete all its reservations and billing history.")
            if st.button("🗑️ Delete this unit", type="secondary"):
                if require_active_subscription():
                    delete_unit(selected_id)
                    st.warning("Unit deleted.")
                    st.rerun()
