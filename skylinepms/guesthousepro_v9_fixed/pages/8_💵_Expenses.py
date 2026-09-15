import streamlit as st
from datetime import date
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.logic import add_expense, list_expenses, delete_expense, EXPENSE_CATEGORIES
from utils.theme import (
    apply_theme, page_header, empty_state, section_label,
    subscription_banner, require_active_subscription, colors, metric_row,
)

st.set_page_config(page_title="Expenses", page_icon="💵", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
account    = get_account(account_id) or {}
currency   = account.get("currency", "UGX")
c = colors()

page_header("Expenses", subtitle="Operating costs · Profit tracking", icon="💵")
subscription_banner()
st.write("")

tab1, tab2 = st.tabs(["📋 All Expenses", "➕ Log Expense"])

# ── Tab 1: All expenses ────────────────────────────────────────────────────────
with tab1:
    today = date.today()
    current_month = today.strftime("%Y-%m")
    filter_month = st.text_input("Filter by month (YYYY-MM)", value=current_month, max_chars=7)

    expenses = list_expenses(account_id=account_id, month=filter_month.strip() or None)
    if not expenses:
        empty_state("No expenses logged for this period.", icon="💵")
    else:
        total = sum(e["amount"] for e in expenses)
        # Group by category
        from collections import defaultdict
        cat_totals = defaultdict(float)
        for e in expenses:
            cat_totals[e["category"]] += e["amount"]

        metric_row([
            {"label": "Total Expenses", "value": f"{currency} {total:,.0f}", "tone": "danger"},
            {"label": "No. of Records", "value": str(len(expenses)), "tone": "neutral"},
        ])

        # Category breakdown
        section_label("By category")
        cat_rows = ""
        for cat, amt in sorted(cat_totals.items(), key=lambda x: -x[1]):
            pct = (amt / total * 100) if total else 0
            cat_rows += (
                f'<div style="display:flex; justify-content:space-between; align-items:center; '
                f'padding:7px 0; border-bottom:1px solid {c["BORDER"]};">'
                f'<span style="font-size:13px;">{cat}</span>'
                f'<div style="text-align:right;">'
                f'<span style="font-size:13px; font-weight:600;">{currency} {amt:,.0f}</span> '
                f'<span style="font-size:11px; color:{c["TEXT_MUTED"]};">({pct:.0f}%)</span>'
                f'</div></div>'
            )
        st.markdown(
            f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
            f'border-radius:14px; padding:0.5rem 1.2rem; margin-bottom:1rem;">{cat_rows}</div>',
            unsafe_allow_html=True,
        )

        section_label("Individual records")
        for e in expenses:
            with st.expander(f"{e['expense_date']} · {e['category']} · {currency} {e['amount']:,.0f} — {e['description'][:40]}"):
                col1, col2 = st.columns(2)
                col1.write(f"**Category:** {e['category']}")
                col1.write(f"**Description:** {e['description']}")
                col1.write(f"**Date:** {e['expense_date']}")
                col2.write(f"**Amount:** {currency} {e['amount']:,.0f}")
                if e["note"]:
                    col2.write(f"**Note:** {e['note']}")
                if st.button("🗑️ Delete", key=f"del_exp_{e['id']}"):
                    if require_active_subscription():
                        delete_expense(e["id"])
                        st.success("Expense deleted.")
                        st.rerun()

# ── Tab 2: Log expense ─────────────────────────────────────────────────────────
with tab2:
    section_label("Log a new expense")
    with st.form("add_expense_form", clear_on_submit=True):
        ec1, ec2 = st.columns(2)
        with ec1:
            e_category    = st.selectbox("Category*", EXPENSE_CATEGORIES)
            e_date        = st.date_input("Date*", value=date.today())
        with ec2:
            e_amount      = st.number_input(f"Amount ({currency})*", min_value=0.0, step=5000.0)
        e_description = st.text_input("Description*", placeholder="e.g. Electricity bill — August")
        e_note        = st.text_input("Note (optional)")
        e_sub         = st.form_submit_button("Log expense", type="primary")
        if e_sub:
            if not require_active_subscription(): pass
            elif not e_description.strip():
                st.error("Description is required.")
            elif e_amount <= 0:
                st.error("Amount must be greater than zero.")
            else:
                add_expense(account_id, e_category, e_description.strip(), e_amount, e_date.isoformat(), e_note.strip())
                st.success(f"Expense logged: {e_category} — {currency} {e_amount:,.0f}")
                st.rerun()
