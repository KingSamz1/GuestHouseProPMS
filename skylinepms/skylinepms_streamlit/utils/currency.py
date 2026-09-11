"""
Currency conversion utility for SkylinePMS.

Fetches live exchange rates from exchangerate-api.com (free tier, no key needed).
Falls back to hardcoded rates if the network call fails or the app is offline.

The subscription fee is anchored at UGX 30,000/month.
All conversions are for display only — billing is always collected in UGX.
"""

import requests
import streamlit as st

BASE_CURRENCY    = "UGX"
MONTHLY_FEE_UGX = 30_000   # anchor — never changes

_FALLBACK_RATES = {
    # How many units of each currency equal 1 UGX
    # i.e.  rate = 1/ugx_per_unit
    "UGX": 1.0,
    "USD": 0.000268,
    "EUR": 0.000248,
    "GBP": 0.000212,
    "KES": 0.034,
    "TZS": 0.68,
    "RWF": 0.30,
    "BIF": 1.25,
    "ETB": 0.015,
    "ZAR": 0.0049,
    "NGN": 0.43,
    "GHS": 0.0040,
    "AED": 0.00098,
    "SAR": 0.00101,
    "INR": 0.023,
    "CNY": 0.00196,
    "AUD": 0.00041,
    "CAD": 0.00037,
    "ZMW": 0.0069,
}

_RATE_TTL = 3600  # seconds — Streamlit caches this


@st.cache_data(ttl=_RATE_TTL, show_spinner=False)
def _fetch_rates() -> dict:
    """Return live rates {currency_code: rate_from_UGX}. Falls back on any error."""
    try:
        r = requests.get(
            "https://api.exchangerate-api.com/v4/latest/UGX",
            timeout=5,
        )
        if r.status_code == 200:
            return r.json().get("rates", _FALLBACK_RATES)
    except Exception:
        pass
    return _FALLBACK_RATES


def get_supported_currencies() -> list:
    """Return all available currencies, priority ones first."""
    rates = _fetch_rates()
    priority = ["UGX", "USD", "EUR", "GBP", "KES", "TZS", "RWF", "ETB",
                "ZAR", "NGN", "GHS", "AED", "SAR", "INR", "AUD", "CAD"]
    others = sorted(c for c in rates if c not in priority)
    return [c for c in priority if c in rates] + others


def convert(amount_ugx: float, to_currency: str) -> float:
    """Convert a UGX amount into another currency using live rates."""
    if to_currency == BASE_CURRENCY:
        return amount_ugx
    rates = _fetch_rates()
    rate = rates.get(to_currency)
    if not rate:
        return amount_ugx
    return amount_ugx * rate


def format_converted(amount_ugx: float, display_currency: str) -> str:
    """
    Return a display string, e.g.:
      'UGX 30,000'                    — when display_currency is UGX
      'UGX 30,000  (≈ USD 8.04)'      — when display_currency is USD
    """
    if display_currency == BASE_CURRENCY:
        return f"UGX {amount_ugx:,.0f}"
    converted = convert(amount_ugx, display_currency)
    if converted < 10:
        c_str = f"{converted:.2f}"
    elif converted < 100:
        c_str = f"{converted:.1f}"
    else:
        c_str = f"{converted:,.0f}"
    return f"UGX {amount_ugx:,.0f}  (≈ {display_currency} {c_str})"


def rate_note(display_currency: str) -> str:
    """Return a short note about the live rate, or '' for UGX."""
    if display_currency == BASE_CURRENCY:
        return ""
    rates = _fetch_rates()
    rate = rates.get(display_currency, 0)
    if not rate:
        return ""
    return (
        f"Live rate: 1 UGX ≈ {rate:.5f} {display_currency}. "
        f"Billing is always in UGX."
    )
