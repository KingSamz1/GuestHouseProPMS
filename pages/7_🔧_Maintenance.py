import streamlit as st
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.logic import (
    list_units, add_maintenance, list_maintenance,
    resolve_maintenance, update_maintenance,
)
from utils.theme import (
from utils.i18n import t
    apply_theme, page_header, empty_state, section_label,
    subscription_banner, require_active_subscription, status_pill, colors,
)

st.set_page_config(page_title="Maintenance", page_icon="🔧", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
account    = get_account(account_id) or {}
currency   = account.get("currency", "UGX")
c = colors()

PRIORITIES = ["high", "medium", "low"]
ISSUE_CATEGORIES = [
    "Plumbing", "Electricity", "Air Conditioning", "TV / Electronics",
    "Refrigerator", "Cooker / Stove", "Wi-Fi / Internet", "Furniture",
    "Locks / Keys", "Water Supply", "Windows / Doors", "General Repair", "Other",
]

page_header("Maintenance", subtitle="Log issues · Assign staff · Block rooms automatically", icon="🔧")
subscription_banner()
st.write("")

tab1, tab2, tab3 = st.tabs(["🔴 Open Issues", "✅ Resolved", "➕ Log Issue"])

# ── Tab 1: Open issues ─────────────────────────────────────────────────────────
with tab1:
    issues = list_maintenance(account_id=account_id, status="open")
    if not issues:
        empty_state("No open maintenance issues. Everything is working! 🎉", icon="✅")
    else:
        st.caption(f"{len(issues)} open issue(s)")
        for issue in issues:
            priority_tone = {"high": "danger", "medium": "warning", "low": "neutral"}.get(issue["priority"], "neutral")
            p_pill = status_pill(issue["priority"].title(), priority_tone)
            with st.expander(
                f"🔴 Unit {issue['unit_number']} — {issue['description'][:50]} · Priority: {issue['priority'].upper()}"
            ):
                col1, col2 = st.columns(2)
                col1.markdown(f"**Priority:** {p_pill}", unsafe_allow_html=True)
                col1.write(f"**Unit:** {issue['unit_type']} — {issue['unit_number']}")
                col1.write(f"**Description:** {issue['description']}")
                col1.write(f"**Reported:** {issue['reported_at'][:16]}")
                col2.write(f"**Assigned to:** {issue['assigned_to'] or 'Unassigned'}")
                col2.write(f"**Estimated cost:** {currency} {issue['cost']:,.0f}" if issue["cost"] else "**Estimated cost:** —")
                col2.write(f"**Notes:** {issue['notes'] or '—'}")

                st.markdown("**Update issue:**")
                with st.form(f"upd_maint_{issue['id']}"):
                    uc1, uc2, uc3 = st.columns(3)
                    with uc1:
                        new_desc  = st.text_input("Description", value=issue["description"])
                        new_prio  = st.selectbox("Priority", PRIORITIES, index=PRIORITIES.index(issue["priority"]))
                    with uc2:
                        new_assign = st.text_input("Assigned to", value=issue["assigned_to"] or "")
                        new_cost   = st.number_input(f"Cost ({currency})", min_value=0.0, value=float(issue["cost"]), step=5000.0)
                    with uc3:
                        new_notes  = st.text_area("Notes", value=issue["notes"] or "", height=68)
                    bc1, bc2 = st.columns(2)
                    save_btn    = bc1.form_submit_button("💾 Save changes", type="primary")
                    resolve_btn = bc2.form_submit_button("✅ Mark resolved")
                    if save_btn:
                        if require_active_subscription():
                            update_maintenance(issue["id"], new_desc, new_prio, new_assign, new_cost, new_notes)
                            st.success("Issue updated.")
                            st.rerun()
                    if resolve_btn:
                        if require_active_subscription():
                            resolve_maintenance(issue["id"])
                            st.success(f"Issue resolved. Unit {issue['unit_number']} set back to available.")
                            st.rerun()

# ── Tab 2: Resolved issues ────────────────────────────────────────────────────
with tab2:
    resolved = list_maintenance(account_id=account_id, status="resolved")
    if not resolved:
        empty_state("No resolved issues yet.", icon="📋")
    else:
        st.caption(f"{len(resolved)} resolved issue(s)")
        total_cost = sum(i["cost"] for i in resolved)
        st.info(f"Total maintenance cost: **{currency} {total_cost:,.0f}**")
        for issue in resolved:
            with st.expander(
                f"✅ Unit {issue['unit_number']} — {issue['description'][:50]} · Resolved: {(issue['resolved_at'] or '')[:10]}"
            ):
                col1, col2 = st.columns(2)
                col1.write(f"**Unit:** {issue['unit_type']} — {issue['unit_number']}")
                col1.write(f"**Description:** {issue['description']}")
                col1.write(f"**Priority:** {issue['priority'].title()}")
                col2.write(f"**Assigned to:** {issue['assigned_to'] or '—'}")
                col2.write(f"**Cost:** {currency} {issue['cost']:,.0f}")
                col2.write(f"**Reported:** {issue['reported_at'][:10]}")
                col2.write(f"**Resolved:** {(issue['resolved_at'] or '')[:10]}")
                if issue["notes"]:
                    st.caption(f"Notes: {issue['notes']}")

# ── Tab 3: Log new issue ───────────────────────────────────────────────────────
with tab3:
    section_label("Log a new maintenance issue")
    units = list_units(account_id=account_id)
    if not units:
        empty_state("No units added yet.", icon="🏘️")
    else:
        with st.form("log_maintenance_form", clear_on_submit=True):
            unit_opts = {f"Unit {u['unit_number']} — {u['unit_type']}": u["id"] for u in units}
            m_unit    = st.selectbox("Unit*", list(unit_opts.keys()))
            mc1, mc2  = st.columns(2)
            with mc1:
                m_category = st.selectbox("Issue category", ISSUE_CATEGORIES)
                m_priority = st.selectbox("Priority*", PRIORITIES, format_func=str.title)
            with mc2:
                m_assign   = st.text_input("Assign to (staff / contractor)")
                m_cost     = st.number_input(f"Estimated cost ({currency})", min_value=0.0, step=5000.0)
            m_desc  = st.text_area("Description*", placeholder="Describe the problem clearly…", height=80)
            m_notes = st.text_area("Additional notes", height=60)
            m_sub   = st.form_submit_button("Log issue (room will be blocked)", type="primary")
            if m_sub:
                if not require_active_subscription(): pass
                elif not m_desc.strip():
                    st.error("Description is required.")
                else:
                    uid   = unit_opts[m_unit]
                    desc  = f"[{m_category}] {m_desc.strip()}"
                    add_maintenance(account_id, uid, desc, m_priority, m_assign.strip(), m_cost, m_notes.strip())
                    st.success(f"Issue logged. {m_unit} has been blocked from new reservations until resolved.")
                    st.rerun()

        st.info("⚠️ When you log a maintenance issue, the unit status is automatically set to **Maintenance** and will not appear as available for booking. Resolving the issue restores it to **Available**.")
