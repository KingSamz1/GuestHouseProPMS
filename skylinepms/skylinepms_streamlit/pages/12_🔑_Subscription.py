import streamlit as st
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.subscription import (
    get_subscription, update_subscription_status, days_remaining,
    subscription_payment_history, redeem_renewal_code,
    generate_renewal_code, list_renewal_codes, is_admin, fast_forward, force_expire,
    MONTHLY_FEE,
)
from utils.theme import apply_theme, page_header, section_label, subscription_banner, colors, metric_row

st.set_page_config(page_title="Subscription", page_icon="🔑", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
account    = get_account(account_id) or {}
currency   = account.get("currency", "UGX")
c = colors()

SUPPORT_WHATSAPP = "https://wa.me/256793839816"
SUPPORT_NUMBER   = "+256 793 839 816"

page_header("Subscription", subtitle="Plan status · Renewal · Payment history", icon="🔑")
st.write("")

sub  = update_subscription_status(account_id)
days = days_remaining(account_id)

if sub:
    status = sub["status"]
    tone   = {"TRIAL": "warning", "ACTIVE": "success", "EXPIRED": "danger"}.get(status, "neutral")
    metric_row([
        {"label": "Plan status",      "value": status,        "tone": tone},
        {"label": "Days remaining",   "value": str(days),     "tone": tone},
        {"label": "Monthly fee",      "value": f"UGX {MONTHLY_FEE:,.0f}", "tone": "neutral"},
    ])
    if status == "TRIAL":
        st.info(f"🎁 Free trial active — expires {sub['trial_end']}. Renew before it ends to keep access.")
    elif status == "ACTIVE":
        st.success(f"✅ Subscription active — next payment due {sub['next_payment_date']}.")
        if sub.get("past_due"):
            st.warning(f"⚠️ Payment overdue — {sub['grace_days_left']} day(s) before account locks. Renew now.")
    else:
        st.error("🔴 Subscription expired. Renew to regain access. Your data is safe.")
else:
    st.warning("No subscription record found for your account. Contact support.")

st.divider()

tab1, tab2, tab3 = st.tabs(
    ["🔄 Renew", "📋 Payment History", "🛠️ Admin (manage accounts)"]
    if is_admin(account_id) else
    ["🔄 Renew", "📋 Payment History", "💬 Support"]
)

# ── Tab 1: Renew ───────────────────────────────────────────────────────────────
with tab1:
    section_label("Renew with a code")
    st.markdown(
        f"Contact support to get a renewal code. Send your payment of **UGX {MONTHLY_FEE:,.0f}/month** via "
        f"MTN MoMo or Airtel Money, then message us for your code."
    )
    with st.form("renew_form"):
        code = st.text_input("Renewal code", placeholder="e.g. A3X9KW2P7F")
        renew_sub = st.form_submit_button("Activate renewal", type="primary")
        if renew_sub:
            try:
                redeem_renewal_code(account_id, code)
                st.success("✅ Subscription renewed successfully! Enjoy SkylinePMS.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    st.divider()
    section_label("Get in touch")
    st.markdown(
        f'<a href="{SUPPORT_WHATSAPP}" target="_blank" style="display:inline-flex; align-items:center; gap:8px; '
        f'background:#25D366; color:#fff; text-decoration:none; font-size:14px; font-weight:600; '
        f'padding:10px 22px; border-radius:9px;">💬 Chat on WhatsApp · {SUPPORT_NUMBER}</a>',
        unsafe_allow_html=True,
    )
    st.caption("We'll confirm your payment and send you a renewal code via WhatsApp.")

# ── Tab 2: Payment history ────────────────────────────────────────────────────
with tab2:
    history = subscription_payment_history(account_id)
    if not history:
        st.info("No subscription payments recorded yet.")
    else:
        for p in history:
            st.markdown(
                f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
                f'border-radius:12px; padding:0.75rem 1rem; margin-bottom:0.5rem;">'
                f'<div style="font-size:13px; font-weight:600;">UGX {p["amount"]:,.0f} — {p["payment_date"]}</div>'
                f'<div style="font-size:12px; color:{c["TEXT_MUTED"]};">'
                f'Method: {p["payment_method"] or "—"} &nbsp;·&nbsp; Ref: {p["transaction_reference"] or "—"}<br>'
                f'Period: {p["period_start"] or "—"} → {p["period_end"] or "—"}'
                f'{(" &nbsp;·&nbsp; " + p["note"]) if p.get("note") else ""}'
                f'</div></div>',
                unsafe_allow_html=True,
            )

# ── Tab 3: Admin or Support ────────────────────────────────────────────────────
with tab3:
    if is_admin(account_id):
        section_label("Generate renewal codes")
        with st.form("gen_code_form"):
            months = st.number_input("Months", min_value=1, max_value=12, value=1, step=1)
            gen_sub = st.form_submit_button("Generate code", type="primary")
            if gen_sub:
                try:
                    code = generate_renewal_code(account_id, int(months))
                    st.success(f"Code: **{code}** ({months} month(s))")
                except Exception as e:
                    st.error(str(e))

        st.divider()
        section_label("All renewal codes")
        try:
            codes = list_renewal_codes(account_id)
            if not codes:
                st.info("No codes generated yet.")
            else:
                for co in codes:
                    used = f"✅ Used by @{co['used_by_username']} on {(co['used_at'] or '')[:10]}" if co["used_by"] else "⏳ Unused"
                    st.markdown(
                        f'`{co["code"]}` — {co["months"]} month(s) — {used}',
                        unsafe_allow_html=False,
                    )
        except Exception as e:
            st.error(str(e))

        st.divider()
        section_label("All accounts")
        from utils.db import list_all_accounts, delete_account
        accs = list_all_accounts()
        for acc in accs:
            if acc["username"].lower() == "samzinov":
                continue
            is_this = acc["id"] == account_id
            with st.expander(f"@{acc['username']} — {acc['property_name']} (ID {acc['id']})"):
                st.write(f"**Currency:** {acc['currency']}")
                st.write(f"**Phone:** {acc['business_phone'] or '—'}")
                st.write(f"**Joined:** {(acc['created_at'] or '')[:10]}")
                acc_sub = get_subscription(acc["id"])
                if acc_sub:
                    st.write(f"**Sub status:** {acc_sub['status']} (trial end: {acc_sub.get('trial_end','—')}, next payment: {acc_sub.get('next_payment_date','—')})")
                dc1, dc2, dc3 = st.columns(3)
                if dc1.button("Fast-forward 3 days", key=f"ff_{acc['id']}"):
                    fast_forward(acc["id"], 3)
                    st.success("Done.")
                    st.rerun()
                if dc2.button("Force expire", key=f"fe_{acc['id']}"):
                    force_expire(acc["id"])
                    st.success("Expired.")
                    st.rerun()
                if dc3.button("🗑️ Delete account", key=f"del_acc_{acc['id']}"):
                    delete_account(acc["id"])
                    st.warning(f"Account {acc['username']} deleted.")
                    st.rerun()
    else:
        section_label("Support")
        st.markdown(
            "For billing questions, renewal assistance, or technical support, contact us via WhatsApp:"
        )
        st.markdown(
            f'<a href="{SUPPORT_WHATSAPP}" target="_blank" style="display:inline-flex; align-items:center; gap:8px; '
            f'background:#25D366; color:#fff; text-decoration:none; font-size:14px; font-weight:600; '
            f'padding:10px 22px; border-radius:9px;">💬 WhatsApp Support · {SUPPORT_NUMBER}</a>',
            unsafe_allow_html=True,
        )
        st.caption("We typically respond within a few hours during business hours (EAT).")
