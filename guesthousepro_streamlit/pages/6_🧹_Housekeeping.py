import streamlit as st
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.logic import (
    list_units, list_housekeeping, update_housekeeping_status,
    create_housekeeping_task, update_unit_status, UNIT_STATUSES,
)
from utils.theme import (
    apply_theme, page_header, empty_state, section_label,
    subscription_banner, require_active_subscription, status_pill, colors,
)

st.set_page_config(page_title="Housekeeping", page_icon="🧹", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
c = colors()

TASK_STATUSES = ["pending", "in_progress", "done"]
TASK_TYPES    = ["checkout_clean", "routine_clean", "inspection", "turndown", "deep_clean", "other"]

page_header("Housekeeping", subtitle="Room status board · Cleaning tasks · Inspections", icon="🧹")
subscription_banner()
st.write("")

tab1, tab2, tab3 = st.tabs(["🗂️ Status Board", "📋 Open Tasks", "➕ Create Task"])

# ── Tab 1: Status board ────────────────────────────────────────────────────────
with tab1:
    section_label("Live room status")
    units = list_units(account_id=account_id)
    if not units:
        empty_state("No units added yet.", icon="🏘️")
    else:
        # Group by status
        buckets = {
            "available":   ("✅ Ready / Available",   "success"),
            "occupied":    ("🟦 Occupied",             "accent"),
            "reserved":    ("🔖 Reserved",             "warning"),
            "dirty":       ("🔴 Dirty (post-checkout)","danger"),
            "cleaning":    ("🧹 Being Cleaned",        "warning"),
            "inspected":   ("🔵 Inspected",            "neutral"),
            "maintenance": ("🔧 Maintenance",          "danger"),
        }

        for status_key, (label, tone) in buckets.items():
            bucket_units = [u for u in units if u["status"] == status_key]
            if not bucket_units:
                continue
            st.markdown(f"**{label}** ({len(bucket_units)})")
            cols = st.columns(min(len(bucket_units), 4))
            for i, u in enumerate(bucket_units):
                with cols[i % 4]:
                    pill = status_pill(u["status"].title(), tone)
                    st.markdown(
                        f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
                        f'border-radius:12px; padding:0.75rem 0.9rem; margin-bottom:0.5rem;">'
                        f'<div style="font-size:14px; font-weight:700; margin-bottom:4px;">Unit {u["unit_number"]}</div>'
                        f'<div style="font-size:12px; color:{c["TEXT_MUTED"]};">{u["unit_type"]}</div>'
                        f'{pill}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        st.divider()
        section_label("Update room status")
        unit_options = {f"Unit {u['unit_number']} — {u['unit_type']} (currently: {u['status']})": u["id"] for u in units}
        selected_label = st.selectbox("Select unit", list(unit_options.keys()))
        selected_id    = unit_options[selected_label]
        current_unit   = next((u for u in units if u["id"] == selected_id), None)

        col_s, col_b = st.columns([2, 1])
        with col_s:
            new_status = st.selectbox(
                "New status", UNIT_STATUSES,
                index=UNIT_STATUSES.index(current_unit["status"]) if current_unit and current_unit["status"] in UNIT_STATUSES else 0,
            )
        with col_b:
            st.write("")
            st.write("")
            if st.button("Update status", type="primary", use_container_width=True):
                if require_active_subscription():
                    update_unit_status(selected_id, new_status)
                    st.success(f"Unit status updated to '{new_status}'.")
                    st.rerun()

        # Housekeeping flow legend
        st.divider()
        st.markdown(
            f'<div style="background:{c["NEUTRAL_SOFT"]}; border:1px solid {c["BORDER"]}; '
            f'border-radius:12px; padding:0.9rem 1.1rem;">'
            f'<p style="font-size:12px; font-weight:700; margin:0 0 8px; color:{c["TEXT_MUTED"]}; '
            f'text-transform:uppercase; letter-spacing:0.06em;">Housekeeping flow</p>'
            f'<p style="font-size:13px; margin:0; color:{c["TEXT_MUTED"]};">'
            f'<strong>OCCUPIED</strong> → <strong>CHECK-OUT</strong> → '
            f'🔴 <strong>DIRTY</strong> → 🧹 <strong>CLEANING</strong> → '
            f'🔵 <strong>INSPECTED</strong> → ✅ <strong>AVAILABLE</strong></p>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Tab 2: Open tasks ──────────────────────────────────────────────────────────
with tab2:
    tasks = list_housekeeping(account_id=account_id)
    if not tasks:
        empty_state("No open housekeeping tasks. Great work! 🎉", icon="✅")
    else:
        st.caption(f"{len(tasks)} open task(s)")
        for t in tasks:
            tone_map = {"pending": "warning", "in_progress": "accent"}
            t_pill   = status_pill(t["status"].replace("_"," ").title(), tone_map.get(t["status"], "neutral"))
            with st.expander(
                f"Unit {t['unit_number']} — {t['task_type'].replace('_',' ').title()} · {t['status']}"
            ):
                col1, col2 = st.columns(2)
                col1.markdown(f"**Status:** {t_pill}", unsafe_allow_html=True)
                col1.write(f"**Unit type:** {t['unit_type']}")
                col1.write(f"**Current room status:** {t['unit_status']}")
                col2.write(f"**Task type:** {t['task_type'].replace('_',' ').title()}")
                col2.write(f"**Assigned to:** {t['assigned_to'] or 'Unassigned'}")
                col2.write(f"**Notes:** {t['notes'] or '—'}")
                col2.write(f"**Created:** {t['created_at'][:16]}")

                st.markdown("**Update task:**")
                uc1, uc2, uc3 = st.columns(3)
                with uc1:
                    new_t_status = st.selectbox("Status", TASK_STATUSES, index=TASK_STATUSES.index(t["status"]) if t["status"] in TASK_STATUSES else 0, key=f"ts_{t['id']}")
                with uc2:
                    new_assigned = st.text_input("Assigned to", value=t["assigned_to"] or "", key=f"ta_{t['id']}")
                with uc3:
                    st.write("")
                    st.write("")
                    if st.button("Update", key=f"tupd_{t['id']}", type="primary"):
                        if require_active_subscription():
                            update_housekeeping_status(t["id"], new_t_status, new_assigned)
                            if new_t_status == "done":
                                # Auto-advance room to inspected
                                update_unit_status(t["unit_id"], "inspected")
                            elif new_t_status == "in_progress":
                                update_unit_status(t["unit_id"], "cleaning")
                            st.success("Task updated.")
                            st.rerun()

# ── Tab 3: Create task ─────────────────────────────────────────────────────────
with tab3:
    section_label("Create a housekeeping task")
    units = list_units(account_id=account_id)
    if not units:
        empty_state("No units added yet.", icon="🏘️")
    else:
        with st.form("create_hk_task", clear_on_submit=True):
            unit_opts = {f"Unit {u['unit_number']} — {u['unit_type']}": u["id"] for u in units}
            hk_unit   = st.selectbox("Unit*", list(unit_opts.keys()))
            hk_type   = st.selectbox("Task type*", TASK_TYPES, format_func=lambda x: x.replace("_"," ").title())
            hk_assign = st.text_input("Assign to (staff name)")
            hk_notes  = st.text_area("Notes", height=70)
            hk_sub    = st.form_submit_button("Create task", type="primary")
            if hk_sub:
                if not require_active_subscription(): pass
                else:
                    uid = unit_opts[hk_unit]
                    create_housekeeping_task(account_id, uid, hk_type, hk_assign.strip(), hk_notes.strip())
                    st.success("Task created.")
                    st.rerun()
