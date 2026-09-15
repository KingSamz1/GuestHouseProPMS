# 🏨 GuesthousePro

**Smart Property & Guest Management for Guesthouses and Serviced Apartments**

GuesthousePro is a Streamlit-based Property Management System (PMS) built for
guesthouses, serviced apartments, and short-stay properties.
It handles reservations, guests, billing, housekeeping, maintenance, expenses,
WhatsApp messaging, and business reports — all in one place.

---

## Features

| Module | What it does |
|---|---|
| 📊 Dashboard | Live occupancy, today's arrivals/departures, revenue, quick actions |
| 🏢 Units | Add and manage all rooms with live status (available, occupied, reserved, cleaning, maintenance) |
| 📅 Reservations | Booking calendar grid, new reservations, availability check |
| 🛎️ Check In / Out | Focused arrival & departure workflow with payment collection |
| 👤 Guests | Guest profiles, ID documents, stay history, search |
| 💰 Billing | Guest folios, extra charges, payments (cash/MoMo/bank), PDF receipts |
| 🧹 Housekeeping | Status board, task management (dirty → cleaning → inspected → available) |
| 🔧 Maintenance | Issue log, priority levels, staff assignment, room blocking |
| 💵 Expenses | Operating cost tracking, category breakdown, P&L |
| 📲 WhatsApp | Booking confirmations, arrival reminders, checkout, post-checkout, custom messages |
| 📊 Reports | Monthly summary, ADR, occupancy %, RevPAR, booking sources, 6-month P&L |
| ⚙️ Settings | Property name, currency, phone, password |
| 🔑 Subscription | Trial & renewal management, renewal codes |

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up secrets
cp .streamlit/secrets.toml.template .streamlit/secrets.toml
# Edit secrets.toml with your username/password and property info

# 3. Run
streamlit run app.py
```

The SQLite database (`data/guesthouse.db`) is created automatically on first run.

---

## Deployment (Streamlit Cloud)

1. Push this folder to a GitHub repository.
2. Connect on [share.streamlit.io](https://share.streamlit.io).
3. Set `app.py` as the entry point.
4. Add your secrets under **App settings → Secrets**.

---

## Directory structure

```
guesthousepro_streamlit/
├── app.py                   # Dashboard (main entry point)
├── requirements.txt
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.template
├── pages/
│   ├── 1_🏢_Units.py
│   ├── 2_📅_Reservations.py
│   ├── 3_👤_Guests.py
│   ├── 4_🛎️_Check_In_Out.py
│   ├── 5_💰_Billing.py
│   ├── 6_🧹_Housekeeping.py
│   ├── 7_🔧_Maintenance.py
│   ├── 8_💵_Expenses.py
│   ├── 9_📊_Reports.py
│   ├── 10_📲_Messages.py
│   ├── 11_⚙️_Settings.py
│   └── 12_🔑_Subscription.py
├── utils/
│   ├── __init__.py
│   ├── db.py          # SQLite schema + account helpers
│   ├── auth.py        # Login / signup
│   ├── logic.py       # Business logic (units, guests, reservations, billing…)
│   ├── theme.py       # Blue/ocean UI palette + shared components
│   ├── whatsapp.py    # Message builders + click-to-chat links
│   ├── receipts.py    # PDF receipt generation (reportlab)
│   └── subscription.py# Trial + renewal + admin codes
├── data/              # SQLite database (auto-created)
├── receipts/          # Generated PDF receipts
└── guest_documents/   # Uploaded ID/passport documents
```

---

## Default admin account

The system creates a hidden admin account (`samzinov`) automatically.
Your own first account is created from `secrets.toml` or via the signup page.

---

## Built with

- [Streamlit](https://streamlit.io)
- [SQLite](https://sqlite.org)
- [ReportLab](https://www.reportlab.com) (PDF receipts)
- [Pandas](https://pandas.pydata.org)

---

*GuesthousePro — distinct from LandlordPro, which handles long-term rental properties.*
*GuesthousePro is purpose-built for guesthouses, serviced apartments, and short-stay hospitality.*
