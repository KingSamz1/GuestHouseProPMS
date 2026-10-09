import streamlit as st
from utils.db import init_db, get_account, update_account_settings, update_account_password
from utils.auth import check_login, logout_button, get_current_account_id
from utils.theme import apply_theme, page_header, section_label, subscription_banner, colors
from utils.i18n import t, language_selector

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
account    = get_account(account_id) or {}
c = colors()

CURRENCIES = [
    ("🇺🇬 UGX — Ugandan Shilling",    "UGX"),
    ("🇰🇪 KES — Kenyan Shilling",     "KES"),
    ("🇹🇿 TZS — Tanzanian Shilling",  "TZS"),
    ("🇷🇼 RWF — Rwandan Franc",       "RWF"),
    ("🇧🇮 BIF — Burundian Franc",     "BIF"),
    ("🇳🇬 NGN — Nigerian Naira",      "NGN"),
    ("🇬🇭 GHS — Ghanaian Cedi",       "GHS"),
    ("🇿🇦 ZAR — South African Rand",  "ZAR"),
    ("🇺🇸 USD — US Dollar",           "USD"),
    ("🇬🇧 GBP — British Pound",       "GBP"),
    ("🇪🇺 EUR — Euro",                "EUR"),
    ("Other (type below)",            None),
]
cu_labels = [l for l, _ in CURRENCIES]
cu_values = {l: v for l, v in CURRENCIES}

DIAL_CODES = [
    ("🇺🇬 UG  +256", "+256"), ("🇰🇪 KE  +254", "+254"), ("🇹🇿 TZ  +255", "+255"),
    ("🇷🇼 RW  +250", "+250"), ("🇳🇬 NG  +234", "+234"), ("🇬🇧 GB  +44",  "+44"),
    ("🇺🇸 US  +1",   "+1"),   ("Other", ""),
]
dc_labels = [l for l, _ in DIAL_CODES]
dc_values = {l: v for l, v in DIAL_CODES}

page_header("Settings", subtitle="Property details · Currency · Password", icon="⚙️")
subscription_banner()
st.write("")

tab1, tab2, tab3 = st.tabs(["🏨 Property Settings", "🔐 Change Password", "🌐 Language"])

# ── Tab 1: Property settings ───────────────────────────────────────────────────
with tab1:
    section_label("Property information")
    with st.form("property_settings_form"):
        prop_name = st.text_input("Property name*", value=account.get("property_name", ""))

        st.markdown("**Currency**")
        current_currency = account.get("currency", "UGX")
        default_cu_idx   = 0
        for idx, (lbl, code) in enumerate(CURRENCIES):
            if code == current_currency:
                default_cu_idx = idx; break
        cu_label   = st.selectbox("Currency", cu_labels, index=default_cu_idx, label_visibility="collapsed")
        cu_code    = cu_values[cu_label]
        if cu_code is None:
            cu_code = st.text_input("Enter currency code", value=current_currency)

        st.markdown("**Business phone**")
        existing_phone = account.get("business_phone", "")
        default_dc_idx = 0
        for idx, (lbl, code) in enumerate(DIAL_CODES):
            if code and existing_phone.startswith(code):
                default_dc_idx = idx; break
        sc1, sc2 = st.columns([1, 2])
        with sc1:
            s_dial_label  = st.selectbox("Dial code", dc_labels, index=default_dc_idx, label_visibility="collapsed")
        with sc2:
            dial_code     = dc_values[s_dial_label]
            local_num     = existing_phone[len(dial_code):] if dial_code and existing_phone.startswith(dial_code) else existing_phone
            s_phone_local = st.text_input("Phone number", value=local_num, placeholder="701 234 567", label_visibility="collapsed")
        new_phone = (dc_values[s_dial_label] + s_phone_local.strip()).strip()

        save_settings = st.form_submit_button("Save settings", type="primary")
        if save_settings:
            if not prop_name.strip():
                st.error("Property name is required.")
            else:
                update_account_settings(account_id, prop_name.strip(), cu_code.strip().upper(), new_phone)
                st.success("Settings saved.")
                st.rerun()

    st.divider()
    section_label("Account info")
    st.write(f"**Username:** @{account.get('username','')}")
    st.write(f"**Account ID:** {account_id}")
    _ca = account.get('created_at') or ''
    _ca_str = _ca.strftime('%Y-%m-%d') if hasattr(_ca, 'strftime') else str(_ca)[:10]
    st.write(f"**Member since:** {_ca_str}")

# ── Tab 2: Change password ─────────────────────────────────────────────────────
with tab2:
    section_label("Change your password")
    from utils.db import verify_password, get_conn, hash_password, update_account_password
    with st.form("change_password_form"):
        old_pass   = st.text_input("Current password", type="password")
        new_pass   = st.text_input("New password (min 6 characters)", type="password")
        conf_pass  = st.text_input("Confirm new password", type="password")
        change_sub = st.form_submit_button("Change password", type="primary")
        if change_sub:
            if not old_pass or not new_pass:
                st.error("All fields are required.")
            elif len(new_pass) < 6:
                st.error("New password must be at least 6 characters.")
            elif new_pass != conf_pass:
                st.error("Passwords do not match.")
            else:
                acc = get_account(account_id)
                if not verify_password(old_pass, acc["password_hash"]):
                    st.error("Current password is incorrect.")
                else:
                    update_account_password(account_id, new_pass)
                    st.success("Password changed successfully.")

with tab3:
    st.markdown("### 🌐 Interface Language")
    st.caption("Choose the language for the entire application.")
    language_selector(location="inline")
