"""
Shared visual styling for SkylinePMS.
Blue/ocean palette — distinct from LandlordPro's green.
Same structure as LandlordPro theme.py so the pattern is familiar.
"""
import streamlit as st

_PALETTES = {
    "light": dict(
        ACCENT="#1A5C8A",
        ACCENT_DARK="#0F3D60",
        ACCENT_SOFT="#E8F3FA",
        DANGER="#B3392E",
        DANGER_SOFT="#FBEAE8",
        WARNING="#A05A00",
        WARNING_SOFT="#FFF3CD",
        SUCCESS="#1F6B3A",
        SUCCESS_SOFT="#E8F5EE",
        NEUTRAL_SOFT="#F4F6F9",
        TEXT="#111C27",
        TEXT_MUTED="#5C6D7E",
        BORDER="#D9E4EE",
        CARD_BG="#FFFFFF",
        SIDEBAR_BG="#F7FAFD",
        BRAND_TEXT="#0D2438",
    ),
    "dark": dict(
        ACCENT="#38BDF8",
        ACCENT_DARK="#7DD3FC",
        ACCENT_SOFT="#0B2A42",
        DANGER="#F87171",
        DANGER_SOFT="#3A1616",
        WARNING="#FBBF24",
        WARNING_SOFT="#2E1F00",
        SUCCESS="#4ADE80",
        SUCCESS_SOFT="#0A2B14",
        NEUTRAL_SOFT="#1A2535",
        TEXT="#E8F0F8",
        TEXT_MUTED="#7A9BB8",
        BORDER="#1E3248",
        CARD_BG="#161F2E",
        SIDEBAR_BG="#101826",
        BRAND_TEXT="#E8F0F8",
    ),
}

RADIUS = "14px"


def _mode():
    try:
        return st.context.theme.type
    except Exception:
        return "light"


def colors():
    return _PALETTES[_mode()]


ACCENT = _PALETTES["light"]["ACCENT"]
ACCENT_DARK = _PALETTES["light"]["ACCENT_DARK"]
ACCENT_SOFT = _PALETTES["light"]["ACCENT_SOFT"]
DANGER = _PALETTES["light"]["DANGER"]
DANGER_SOFT = _PALETTES["light"]["DANGER_SOFT"]
TEXT_MUTED = _PALETTES["light"]["TEXT_MUTED"]
BORDER = _PALETTES["light"]["BORDER"]


def apply_theme():
    c = colors()
    st.markdown(
        f"""
        <style>
        .block-container {{
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 960px;
        }}
        h1, h2, h3 {{ letter-spacing: -0.01em; font-weight: 650; }}
        p, label, .stMarkdown {{ color: {c['TEXT']}; }}

        section[data-testid="stSidebar"] {{
            background-color: {c['SIDEBAR_BG']};
            border-right: 1px solid {c['BORDER']};
        }}
        section[data-testid="stSidebar"] .stButton button {{ border-radius: 10px; }}

        .stButton button, .stDownloadButton button, .stFormSubmitButton button, .stLinkButton a {{
            border-radius: 10px;
            border: 1px solid {c['BORDER']};
            font-weight: 500;
            padding: 0.5rem 1.1rem;
            transition: all 0.15s ease;
        }}
        .stButton button:hover, .stDownloadButton button:hover, .stFormSubmitButton button:hover {{
            border-color: {c['ACCENT']};
            color: {c['ACCENT']};
        }}
        button[kind="primary"] {{ background-color: {c['ACCENT']} !important; border: none !important; }}
        button[kind="primary"]:hover {{ background-color: {c['ACCENT_DARK']} !important; color: #fff !important; }}

        .stTextInput input, .stNumberInput input, .stDateInput input,
        .stSelectbox div[data-baseweb="select"] > div, .stTextArea textarea {{
            border-radius: 10px !important;
            border: 1px solid {c['BORDER']} !important;
        }}

        div[data-testid="stForm"] {{
            border: 1px solid {c['BORDER']};
            border-radius: {RADIUS};
            padding: 1.5rem 1.5rem 0.5rem;
            background-color: transparent;
        }}

        div[data-testid="stExpander"] {{
            border: 1px solid {c['BORDER']};
            border-radius: {RADIUS};
            box-shadow: 0 1px 2px rgba(0,0,0,0.02);
        }}
        div[data-testid="stExpander"] summary {{ font-weight: 550; }}

        div[data-testid="stDataFrame"] {{
            border: 1px solid {c['BORDER']};
            border-radius: 10px;
            overflow: hidden;
        }}

        hr {{ margin: 1.75rem 0; border-color: {c['BORDER']}; }}
        div[data-testid="stAlert"] {{ border-radius: 10px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title, subtitle=None, icon=None):
    c = colors()
    icon_html = f'<span style="margin-right:8px;">{icon}</span>' if icon else ""
    st.markdown(f'<h2 style="margin-bottom:0.15rem;">{icon_html}{title}</h2>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<p style='color:{c['TEXT_MUTED']}; margin-top:-0.4rem;'>{subtitle}</p>", unsafe_allow_html=True)


def section_label(text):
    c = colors()
    st.markdown(
        f"<p style='color:{c['TEXT_MUTED']}; font-size:0.8rem; font-weight:600; "
        f"text-transform:uppercase; letter-spacing:0.06em; margin-bottom:0.3rem;'>{text}</p>",
        unsafe_allow_html=True,
    )


def empty_state(message, icon="📭"):
    c = colors()
    html = (
        f'<div style="text-align:center; padding:2.5rem 1rem; color:{c["TEXT_MUTED"]}; '
        f'background-color:{c["ACCENT_SOFT"]}; border-radius:{RADIUS}; border:1px dashed {c["BORDER"]};">'
        f'<div style="font-size:1.8rem; margin-bottom:0.4rem;">{icon}</div>'
        f'<div>{message}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def metric_row(metrics):
    c = colors()
    tone_styles = {
        "neutral": (c["NEUTRAL_SOFT"], c["BRAND_TEXT"], c["TEXT_MUTED"]),
        "accent":  (c["ACCENT_SOFT"],  c["ACCENT_DARK"], c["ACCENT"]),
        "danger":  (c["DANGER_SOFT"],  c["DANGER"],  c["DANGER"]),
        "success": (c["SUCCESS_SOFT"], c["SUCCESS"], c["SUCCESS"]),
        "warning": (c["WARNING_SOFT"], c["WARNING"], c["WARNING"]),
    }
    tiles = ""
    for m in metrics:
        bg, value_color, label_color = tone_styles.get(m.get("tone", "neutral"), tone_styles["neutral"])
        tiles += (
            f'<div style="background:{bg}; border-radius:10px; padding:1rem 1.1rem; flex:1; min-width:130px;">'
            f'<p style="font-size:12px; color:{label_color}; margin:0 0 4px; font-weight:500;">{m["label"]}</p>'
            f'<p style="font-size:22px; font-weight:650; margin:0; color:{value_color};">{m["value"]}</p>'
            f'</div>'
        )
    st.markdown(f'<div style="display:flex; gap:12px; flex-wrap:wrap; margin-bottom:1rem;">{tiles}</div>', unsafe_allow_html=True)


def status_pill(text, tone="neutral"):
    c = colors()
    styles = {
        "success":  (c["SUCCESS_SOFT"],  c["SUCCESS"]),
        "danger":   (c["DANGER_SOFT"],   c["DANGER"]),
        "warning":  (c["WARNING_SOFT"],  c["WARNING"]),
        "accent":   (c["ACCENT_SOFT"],   c["ACCENT_DARK"]),
        "neutral":  (c["NEUTRAL_SOFT"],  c["TEXT_MUTED"]),
    }
    bg, color = styles.get(tone, styles["neutral"])
    return (
        f'<span style="background:{bg}; color:{color}; font-size:12px; font-weight:600; '
        f'padding:3px 10px; border-radius:999px; white-space:nowrap;">{text}</span>'
    )


def unit_status_tone(status):
    return {
        "available":   "success",
        "occupied":    "accent",
        "reserved":    "warning",
        "cleaning":    "warning",
        "maintenance": "danger",
        "dirty":       "danger",
        "inspected":   "neutral",
    }.get(status, "neutral")


def subscription_banner():
    from utils.subscription import update_subscription_status, days_remaining, is_admin
    from utils.auth import get_current_account_id
    account_id = get_current_account_id()
    if is_admin(account_id):
        return
    sub = update_subscription_status(account_id)
    if not sub:
        return
    status = sub["status"]
    days = days_remaining(account_id)
    if status == "TRIAL":
        if sub.get("past_due"):
            st.warning(f"⏳ Free trial ended — {sub['grace_days_left']} day(s) before account locks. Renew on the Subscription page.")
        elif days <= 2:
            st.info(f"⏰ Free trial ends in {days} day(s). Renew soon.")
        else:
            st.info(f"🎁 SkylinePMS free trial — {days} day(s) remaining")
    elif status == "ACTIVE":
        if sub.get("past_due"):
            st.warning(f"⏳ Payment overdue — {sub['grace_days_left']} day(s) left before account locks.")
        elif days <= 2:
            st.info(f"⏰ Subscription renews in {days} day(s).")
    else:
        st.error("🔴 SkylinePMS subscription expired — renew on the Subscription page.")


def require_active_subscription():
    from utils.subscription import system_active, is_admin
    from utils.auth import get_current_account_id
    account_id = get_current_account_id()
    if is_admin(account_id) or system_active(account_id):
        return True
    st.error("🔒 Your SkylinePMS subscription has expired. Your data is safe — renew on the **Subscription** page to continue.")
    return False
