import streamlit as st
from datetime import date
from collections import defaultdict
from utils.db import init_db, get_account
from utils.auth import check_login, logout_button, get_current_account_id
from utils.logic import (
    list_reservations, list_payments, list_expenses,
    revenue_by_source, monthly_summary, list_units, dashboard_summary,
)
from utils.theme import (
    apply_theme, page_header, empty_state, section_label,
    subscription_banner, require_active_subscription, metric_row, colors,
)

st.set_page_config(page_title="Reports", page_icon="📊", layout="wide")
apply_theme()
init_db()
if not check_login():
    st.stop()
logout_button()

account_id = get_current_account_id()
account    = get_account(account_id) or {}
currency   = account.get("currency", "UGX")
c = colors()

page_header("Reports", subtitle="Occupancy · Revenue · Booking sources · Profit & Loss", icon="📊")
subscription_banner()
st.write("")

today = date.today()
current_month = today.strftime("%Y-%m")

tab1, tab2, tab3, tab4 = st.tabs(["📅 Monthly Summary", "📈 Booking Sources", "🏠 Occupancy", "💹 P&L Overview"])

# ── Tab 1: Monthly summary ─────────────────────────────────────────────────────
with tab1:
    report_month = st.text_input("Month (YYYY-MM)", value=current_month, max_chars=7, key="rep_month")
    if report_month.strip():
        m = report_month.strip()
        summary = monthly_summary(account_id, m)

        metric_row([
            {"label": "Revenue",      "value": f"{currency} {summary['revenue']:,.0f}",  "tone": "accent"},
            {"label": "Expenses",     "value": f"{currency} {summary['expenses']:,.0f}", "tone": "danger"},
            {"label": "Net (Revenue – Expenses)",
                                       "value": f"{currency} {summary['net']:,.0f}",
                                       "tone": "success" if summary["net"] >= 0 else "danger"},
            {"label": "Bookings",     "value": str(summary["bookings"]),                  "tone": "neutral"},
            {"label": "Nights Sold",  "value": str(summary["nights_sold"]),               "tone": "neutral"},
        ])

        units_count = len(list_units(account_id=account_id))
        # ADR
        adr = summary["revenue"] / summary["nights_sold"] if summary["nights_sold"] else 0
        # Days in month
        import calendar
        try:
            year_i, mon_i = int(m[:4]), int(m[5:])
            days_in_month = calendar.monthrange(year_i, mon_i)[1]
        except Exception:
            days_in_month = 30
        avail_nights = units_count * days_in_month
        occupancy_pct = round((summary["nights_sold"] / avail_nights * 100) if avail_nights else 0, 1)
        revpar = summary["revenue"] / avail_nights if avail_nights else 0

        st.write("")
        metric_row([
            {"label": "ADR (Avg Daily Rate)",  "value": f"{currency} {adr:,.0f}",       "tone": "accent"},
            {"label": "Occupancy %",           "value": f"{occupancy_pct}%",             "tone": "accent"},
            {"label": "RevPAR",                "value": f"{currency} {revpar:,.0f}",     "tone": "accent"},
        ])
        st.caption("ADR = Revenue ÷ Nights Sold · RevPAR = Revenue ÷ Available Room Nights")

        # Revenue by booking source this month
        sources = revenue_by_source(account_id, month=m)
        if sources:
            st.write("")
            section_label("Revenue by booking source")
            total_rev = sum(s["total"] for s in sources)
            src_rows = ""
            for s in sources:
                pct = (s["total"] / total_rev * 100) if total_rev else 0
                src_rows += (
                    f'<div style="display:flex; justify-content:space-between; align-items:center; '
                    f'padding:7px 0; border-bottom:1px solid {c["BORDER"]};">'
                    f'<span style="font-size:13px;">{s["booking_source"]}</span>'
                    f'<div style="text-align:right;">'
                    f'<span style="font-size:13px; font-weight:600;">{currency} {s["total"]:,.0f}</span> '
                    f'<span style="font-size:11px; color:{c["TEXT_MUTED"]};">({pct:.0f}%) · {s["bookings"]} booking(s)</span>'
                    f'</div></div>'
                )
            st.markdown(
                f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
                f'border-radius:14px; padding:0.5rem 1.2rem;">{src_rows}</div>',
                unsafe_allow_html=True,
            )

        # Daily revenue breakdown
        payments_month = list_payments(account_id=account_id)
        payments_month = [p for p in payments_month if p["payment_date"].startswith(m)]
        if payments_month:
            st.write("")
            section_label("Daily payments this month")
            daily = defaultdict(float)
            for p in payments_month:
                daily[p["payment_date"]] += p["amount"]
            rows = ""
            for d in sorted(daily.keys()):
                rows += (
                    f'<div style="display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid {c["BORDER"]};">'
                    f'<span style="font-size:13px;">{d}</span>'
                    f'<span style="font-size:13px; font-weight:600;">{currency} {daily[d]:,.0f}</span>'
                    f'</div>'
                )
            st.markdown(
                f'<div style="background:{c["CARD_BG"]}; border:1px solid {c["BORDER"]}; '
                f'border-radius:14px; padding:0.5rem 1.2rem;">{rows}</div>',
                unsafe_allow_html=True,
            )

# ── Tab 2: Booking sources ────────────────────────────────────────────────────
with tab2:
    src_month = st.text_input("Month (YYYY-MM or leave blank for all time)", value="", key="src_month")
    sources = revenue_by_source(account_id, month=src_month.strip() or None)
    if not sources:
        empty_state("No bookings recorded yet.", icon="📈")
    else:
        total_rev = sum(s["total"] for s in sources)
        total_bk  = sum(s["bookings"] for s in sources)

        metric_row([
            {"label": "Total Revenue",  "value": f"{currency} {total_rev:,.0f}", "tone": "accent"},
            {"label": "Total Bookings", "value": str(total_bk),                  "tone": "neutral"},
        ])

        section_label("Revenue by booking source")
        for s in sources:
            pct = (s["total"] / total_rev * 100) if total_rev else 0
            bar_width = max(int(pct), 2)
            st.markdown(
                f'<div style="margin-bottom:10px;">'
                f'<div style="display:flex; justify-content:space-between; margin-bottom:3px;">'
                f'<span style="font-size:13px; font-weight:500;">{s["booking_source"]}</span>'
                f'<span style="font-size:13px; color:{c["TEXT_MUTED"]};">'
                f'{currency} {s["total"]:,.0f} · {s["bookings"]} booking(s) · {pct:.1f}%</span>'
                f'</div>'
                f'<div style="background:{c["NEUTRAL_SOFT"]}; border-radius:6px; height:8px;">'
                f'<div style="background:{c["ACCENT"]}; border-radius:6px; height:8px; width:{bar_width}%;"></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

# ── Tab 3: Occupancy ──────────────────────────────────────────────────────────
with tab3:
    occ_month = st.text_input("Month (YYYY-MM)", value=current_month, max_chars=7, key="occ_month")
    if occ_month.strip():
        m = occ_month.strip()
        resos = list_reservations(account_id=account_id)
        month_resos = [r for r in resos if r["check_in_date"].startswith(m) and r["status"] != "cancelled"]
        units = list_units(account_id=account_id)

        import calendar
        try:
            year_i, mon_i = int(m[:4]), int(m[5:])
            days_in_month = calendar.monthrange(year_i, mon_i)[1]
        except Exception:
            days_in_month = 30

        # Per-unit occupancy
        if not units:
            empty_state("No units.", icon="🏘️")
        else:
            section_label("Occupancy by unit")
            for u in units:
                unit_resos = [r for r in month_resos if r["unit_id"] == u["id"]]
                nights_occupied = sum(r["num_nights"] for r in unit_resos)
                occ_pct = round((nights_occupied / days_in_month * 100) if days_in_month else 0, 1)
                bar_w = max(int(occ_pct), 2)
                st.markdown(
                    f'<div style="margin-bottom:10px;">'
                    f'<div style="display:flex; justify-content:space-between; margin-bottom:3px;">'
                    f'<span style="font-size:13px; font-weight:500;">Unit {u["unit_number"]} ({u["unit_type"]})</span>'
                    f'<span style="font-size:12px; color:{c["TEXT_MUTED"]};">{nights_occupied}/{days_in_month} nights · {occ_pct}%</span>'
                    f'</div>'
                    f'<div style="background:{c["NEUTRAL_SOFT"]}; border-radius:6px; height:8px;">'
                    f'<div style="background:{c["ACCENT"]}; border-radius:6px; height:8px; width:{bar_w}%;"></div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

            # Overall
            total_nights = days_in_month * len(units)
            sold_nights  = sum(r["num_nights"] for r in month_resos)
            overall_pct  = round((sold_nights / total_nights * 100) if total_nights else 0, 1)
            st.write("")
            metric_row([
                {"label": "Overall Occupancy", "value": f"{overall_pct}%",       "tone": "accent"},
                {"label": "Nights Sold",       "value": str(sold_nights),        "tone": "neutral"},
                {"label": "Available Nights",  "value": str(total_nights),       "tone": "neutral"},
                {"label": "Bookings",          "value": str(len(month_resos)),   "tone": "neutral"},
            ])

# ── Tab 4: P&L overview ───────────────────────────────────────────────────────
with tab4:
    section_label("Profit & Loss — last 6 months")
    months = []
    y, mo = today.year, today.month
    for _ in range(6):
        months.append(f"{y}-{mo:02d}")
        mo -= 1
        if mo == 0:
            mo = 12; y -= 1
    months.reverse()

    rows = []
    for m in months:
        s = monthly_summary(account_id, m)
        rows.append({
            "Month": m,
            f"Revenue ({currency})":  f"{s['revenue']:,.0f}",
            f"Expenses ({currency})": f"{s['expenses']:,.0f}",
            f"Net ({currency})":      f"{s['net']:,.0f}",
            "Bookings": str(s["bookings"]),
        })

    import pandas as pd
    df = pd.DataFrame(rows).set_index("Month")
    st.dataframe(df, use_container_width=True)

    # Grand totals
    all_rev  = sum(monthly_summary(account_id, m)["revenue"] for m in months)
    all_exp  = sum(monthly_summary(account_id, m)["expenses"] for m in months)
    all_net  = all_rev - all_exp
    metric_row([
        {"label": "6-Month Revenue",  "value": f"{currency} {all_rev:,.0f}", "tone": "accent"},
        {"label": "6-Month Expenses", "value": f"{currency} {all_exp:,.0f}", "tone": "danger"},
        {"label": "6-Month Net",      "value": f"{currency} {all_net:,.0f}",
         "tone": "success" if all_net >= 0 else "danger"},
    ])
