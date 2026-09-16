import streamlit as st
from datetime import date
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.logic import add_guest, list_guests, get_guest, update_guest, search_guests, save_guest_id_document, update_guest_id_document, list_reservations
from utils.theme import apply_theme, page_header, empty_state, section_label, subscription_banner, require_active_subscription, colors

st.set_page_config(page_title="Guests", page_icon="👤", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
account    = get_account(account_id) or {}
currency   = account.get("currency", "UGX")
c = colors()

DIAL_CODES = [
    ("🇺🇬 UG  +256", "+256"), ("🇰🇪 KE  +254", "+254"), ("🇹🇿 TZ  +255", "+255"),
    ("🇷🇼 RW  +250", "+250"), ("🇧🇮 BI  +257", "+257"), ("🇸🇸 SS  +211", "+211"),
    ("🇨🇩 CD  +243", "+243"), ("🇳🇬 NG  +234", "+234"), ("🇬🇭 GH  +233", "+233"),
    ("🇿🇦 ZA  +27",  "+27"),  ("🇬🇧 GB  +44",  "+44"),  ("🇺🇸 US  +1",   "+1"),
    ("🇩🇪 DE  +49",  "+49"),  ("🇫🇷 FR  +33",  "+33"),  ("🇮🇳 IN  +91",  "+91"),
    ("🇨🇳 CN  +86",  "+86"),  ("🇸🇦 SA  +966", "+966"), ("🇦🇪 AE  +971", "+971"),
    ("🇦🇺 AU  +61",  "+61"),  ("Other", ""),
]
dc_labels = [l for l, _ in DIAL_CODES]
dc_values = {l: v for l, v in DIAL_CODES}

page_header("Guest Profiles", subtitle="Guest database · Stay history · Preferences", icon="👤")
subscription_banner()
st.write("")

tab1, tab2, tab3 = st.tabs(["👥 All Guests", "➕ Add Guest", "🔍 Search"])

# ── Tab 1: All guests ──────────────────────────────────────────────────────────
with tab1:
    guests = list_guests(account_id=account_id)
    if not guests:
        empty_state("No guests yet. Add your first guest in the 'Add Guest' tab..", icon="👤")
    else:
        st.caption(f"{len(guests)} guest(s) on file")
        for g in guests:
            with st.expander(
                f"{g['full_name']} · {g['phone'] or 'no phone'} · {g['total_stays']} stay(s) · {currency} {g['total_spent']:,.0f} total spent"
            ):
                edit_key = f"edit_guest_{g['id']}"
                if st.session_state.get(edit_key):
                    # Edit form
                    with st.form(f"edit_guest_form_{g['id']}"):
                        e_name = st.text_input("Full name*", value=g["full_name"])
                        st.markdown("**Phone**")
                        existing_phone = g["phone"] or ""
                        default_idx = 0
                        for idx, (lbl, code) in enumerate(DIAL_CODES):
                            if code and existing_phone.startswith(code):
                                default_idx = idx; break
                        ec1, ec2 = st.columns([1, 2])
                        with ec1:
                            e_dial = st.selectbox("Code", dc_labels, index=default_idx, label_visibility="collapsed", key=f"edial_{g['id']}")
                        with ec2:
                            dial_code = dc_values[e_dial]
                            local = existing_phone[len(dial_code):] if dial_code and existing_phone.startswith(dial_code) else existing_phone
                            e_phone_local = st.text_input("Number", value=local, label_visibility="collapsed", key=f"ephone_{g['id']}")
                        e_phone = (dc_values[e_dial] + e_phone_local.strip()).strip()
                        e_email = st.text_input("Email", value=g["email"])
                        e_nat   = st.text_input("Nationality", value=g["nationality"])
                        e_id    = st.text_input("ID / Passport Number", value=g["id_number"])
                        e_co    = st.text_input("Company", value=g["company"])
                        e_req   = st.text_input("Preferences / Special requests", value=g["special_requests"])
                        cs, cc  = st.columns(2)
                        save   = cs.form_submit_button("Save", type="primary")
                        cancel = cc.form_submit_button("Cancel")
                        if save:
                            if not require_active_subscription(): pass
                            elif not e_name.strip(): st.error("Name required.")
                            else:
                                update_guest(g["id"], e_name.strip(), e_phone, e_email, e_nat, e_id, e_co, e_req)
                                st.session_state[edit_key] = False
                                st.success("Guest updated.")
                                st.rerun()
                        if cancel:
                            st.session_state[edit_key] = False
                            st.rerun()
                else:
                    col1, col2, col3 = st.columns(3)
                    col1.write(f"**Phone:** {g['phone'] or '—'}")
                    col1.write(f"**Email:** {g['email'] or '—'}")
                    col1.write(f"**Nationality:** {g['nationality'] or '—'}")
                    col2.write(f"**ID/Passport:** {g['id_number'] or '—'}")
                    col2.write(f"**Company:** {g['company'] or '—'}")
                    col2.write(f"**Special requests:** {g['special_requests'] or '—'}")
                    col3.write(f"**Total stays:** {g['total_stays']}")
                    col3.write(f"**Total spent:** {currency} {g['total_spent']:,.0f}")

                    # ID document
                    if g.get("id_document_path"):
                        st.markdown("**ID document on file:**")
                        doc = g["id_document_path"]
                        if doc.lower().endswith((".png", ".jpg", ".jpeg")):
                            st.image(doc, width=280)
                        else:
                            with open(doc, "rb") as f:
                                st.download_button("📄 Download ID document", f, file_name=doc.split("/")[-1], key=f"iddoc_{g['id']}")
                    else:
                        uploaded = st.file_uploader(
                            "Attach ID / Passport document", type=["png","jpg","jpeg","pdf"],
                            key=f"upload_id_{g['id']}",
                        )
                        if uploaded:
                            path = save_guest_id_document(g["id"], uploaded)
                            update_guest_id_document(g["id"], path)
                            st.success("ID document attached.")
                            st.rerun()

                    # Stay history
                    stays = list_reservations(account_id=account_id)
                    guest_stays = [r for r in stays if r["guest_id"] == g["id"]]
                    if guest_stays:
                        st.markdown("**Stay history:**")
                        for r in guest_stays[:5]:
                            st.caption(f"• {r['check_in_date']} → {r['check_out_date']} · Unit {r['unit_number']} · {r['status']} · {r['booking_ref']}")

                    if st.button("✏️ Edit guest", key=f"edit_btn_{g['id']}"):
                        st.session_state[edit_key] = True
                        st.rerun()

# ── Tab 2: Add guest ───────────────────────────────────────────────────────────
with tab2:
    section_label("Add a new guest")
    with st.form("add_guest_form", clear_on_submit=True):
        full_name = st.text_input("Full name*")
        st.markdown("**Phone**")
        pc1, pc2 = st.columns([1, 2])
        with pc1:
            dial_label = st.selectbox("Code", dc_labels, index=0, label_visibility="collapsed")
        with pc2:
            phone_local = st.text_input("Number", placeholder="701 234 567", label_visibility="collapsed")
        phone     = (dc_values[dial_label] + phone_local.strip()).strip()
        email     = st.text_input("Email")
        nationality = st.text_input("Nationality")
        id_number = st.text_input("National ID or Passport number")
        id_photo  = st.file_uploader("ID/Passport document (optional)", type=["png","jpg","jpeg","pdf"])
        company   = st.text_input("Company / Organisation")
        special_requests = st.text_input("Preferences / Special requests (e.g. high floor, quiet room)")
        submitted = st.form_submit_button("Add guest", type="primary")
        if submitted:
            if not require_active_subscription(): pass
            elif not full_name.strip():
                st.error("Full name is required.")
            else:
                gid = add_guest(account_id, full_name.strip(), phone.strip(), email.strip(),
                                nationality.strip(), id_number.strip(), company.strip(), special_requests.strip())
                if id_photo:
                    path = save_guest_id_document(gid, id_photo)
                    update_guest_id_document(gid, path)
                st.success(f"Guest '{full_name}' added.")
                st.rerun()

# ── Tab 3: Search ──────────────────────────────────────────────────────────────
with tab3:
    section_label("Search guests")
    query = st.text_input("Search by name, phone, or email", placeholder="e.g. Sarah, +25678...")
    if query.strip():
        results = search_guests(account_id, query.strip())
        if not results:
            empty_state("No guests found matching that search.", icon="🔍")
        else:
            for g in results:
                st.markdown(
                    f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
                    f'border-radius:12px; padding:0.75rem 1rem; margin-bottom:0.5rem;">'
                    f'<strong>{g["full_name"]}</strong> &nbsp;·&nbsp; {g["phone"] or "no phone"} &nbsp;·&nbsp; '
                    f'{g["nationality"] or ""} &nbsp;·&nbsp; {g["total_stays"]} stay(s) &nbsp;·&nbsp; '
                    f'{currency} {g["total_spent"]:,.0f} total</div>',
                    unsafe_allow_html=True,
                )
