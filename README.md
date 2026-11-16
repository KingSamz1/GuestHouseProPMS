# GuesthousePro — Property Management System

GuesthousePro is a Python and Streamlit application for managing guesthouses, serviced apartments and short-stay accommodation.

It brings together room availability, reservations, guest records, check-in and check-out, billing, housekeeping, maintenance, expenses, messaging and operating reports.

## Project overview

- **Project:** GuesthousePro Property Management System (PMS)
- **Developer:** Samuel — [@KingSamz1](https://github.com/KingSamz1)
- **Technology:** Python, Streamlit, PostgreSQL, Pandas and ReportLab
- **Status:** Independently developed application / evolving MVP

## Main application areas

| Area | Purpose |
|---|---|
| Dashboard | Occupancy, arrivals, departures and business overview |
| Units | Room details and availability/status management |
| Reservations | Booking records and availability workflows |
| Check-in / check-out | Guest arrival and departure process |
| Guests | Guest profiles, documents and stay history |
| Billing | Charges, payments and PDF receipts |
| Housekeeping | Cleaning tasks and room status updates |
| Maintenance | Maintenance issue records and task tracking |
| Expenses | Operating expense records |
| Messages | Guest message preparation and WhatsApp click-to-chat links |
| Reports | Occupancy, revenue and business summaries |
| Settings | Property profile, currency, contact details and password |
| Subscription | Trial and renewal-code screens |

## Technology and architecture

- **Python** — application and business logic
- **Streamlit** — interactive web interface
- **PostgreSQL** — persistent relational database
- **Psycopg2** — PostgreSQL connection pooling and database access
- **Pandas** — report tables and data handling
- **ReportLab** — PDF receipt generation

The database connection is configured through Streamlit secrets and uses SSL.

## Repository structure

```text
app.py                  Streamlit application entry point
pages/                  Units, reservations, guests, billing and other modules
utils/db.py             PostgreSQL connection pool, schema and account helpers
utils/pg.py             Shared PostgreSQL query helpers
utils/logic.py          Guesthouse, reservation, billing and operations logic
utils/auth.py           Login, registration and password-reset interface
utils/receipts.py       PDF receipt generation
utils/whatsapp.py       Guest message preparation and click-to-chat links
utils/subscription.py   Trial, renewal and administrator functions
utils/theme.py          Shared interface styling and components
utils/i18n.py           Language and translation support
requirements.txt        Python dependencies
```

## Run locally

1. Install Python 3.10 or newer.
2. Clone this repository and open its folder.
3. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   # Linux/macOS
   source .venv/bin/activate
   # Windows PowerShell
   .venv\\Scripts\\Activate.ps1
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Create `.streamlit/secrets.toml` locally and provide your own PostgreSQL connection and first-account details:

   ```toml
   [database]
   host = "YOUR-POSTGRES-HOST"
   port = 5432
   database = "postgres"
   user = "YOUR-DATABASE-USER"
   password = "YOUR-DATABASE-PASSWORD"

   [auth]
   username = "YOUR_INITIAL_USERNAME"
   password = "YOUR_INITIAL_PASSWORD"

   [property]
   property_name = "Your Property Name"
   currency = "UGX"
   phone = ""

   # Optional: provisions the reserved administrator account
   # only when that account does not already exist.
   [admin]
   password = "A-UNIQUE-STRONG-ADMIN-PASSWORD"
   ```

6. Start the application:

   ```bash
   streamlit run app.py
   ```

The `[auth]` section is read only when the database has no accounts yet. The optional `[admin]` password provisions the administrator account on a fresh database; it does not reset an existing administrator password. Existing account passwords can be changed in the application's Settings page.

Never commit real secrets, guest records, identity documents, database backups or generated receipts.

## Current implementation notes

- Guest and reservation records, billing, payments, housekeeping, maintenance and expenses are represented in the application.
- WhatsApp messages are prepared as prefilled click-to-chat links. Automated sending through a WhatsApp Business API provider is not included in the current messaging module.
- Payment methods and references can be recorded in the application; an automated payment-provider reconciliation integration should be assessed separately.
- The current password helper uses salted SHA-256. A password-specific password-hashing algorithm should be adopted before production use.
- Record-level account authorization, guest-document access, backups, audit logging, upload validation and production deployment security need further review before storing real guests' sensitive records.

This repository is shared as a software-development portfolio and demonstration. Do not use it with real guest identity documents or payment records without completing a security review and configuring appropriate access controls, backups and deployment protections.

## Developer

Built by **Samuel** as an independent software project exploring practical application development, database-backed workflows, hospitality operations and business process automation.

GitHub: [@KingSamz1](https://github.com/KingSamz1)
