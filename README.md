# Elevator Chip API

Production-oriented Flask-RESTX API for managing elevator chip access, door subscriptions, users, and balances.

## Features

- **JWT authentication** with proper 401 responses for missing/invalid tokens
- **Role-based access** (`admin`, `user`) with seeded admin account
- **Admin-only user registration** (phone, ID number, optional email)
- **Buildings** and **subscriptions** (billing per door; separate from physical chips)
- **Chips** as independent entities — assign, activate, deactivate
- **Balance model** — payments increase balance; monthly fees decrease it (can go negative)
- **CSV payment import** for admin bulk uploads
- **Password change** endpoint for users
- **Structured logging** with rotating file output
- **APScheduler** — daily billing job for due subscriptions
- **Georgia-first phone validation** with international E.164 support

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env            # edit secrets before production
python run.py
```

API docs: [http://localhost:5000/api/v1/docs](http://localhost:5000/api/v1/docs)

Web UI: [http://localhost:5000/](http://localhost:5000/) (login page at `/auth/login`)

Default admin (change in `.env`):

| Field    | Default value        |
|----------|----------------------|
| Phone    | `+995591000001`      |
| Password | `ChangeMeAdmin123!`  |

> **Note:** If upgrading from an earlier schema, delete `elevator_chip.db` or run migrations so new tables/columns are created.

## Web frontend (Jinja templates)

Session-based UI alongside the REST API:

| URL | Role | Pages |
|-----|------|-------|
| `/auth/login` | Public | Login |
| `/admin/*` | Admin | Dashboard, users, buildings, subscriptions, chips, CSV import |
| `/dashboard/*` | User | Dashboard, subscriptions, chips, transactions, profile, password |

Structure:

```
app/
  web/              Blueprints (auth, admin, user, main)
  templates/        base.html, components, admin/, user/, errors/
  static/           css/main.css, js/main.js
```

The web layer reuses the same service classes as the API (no duplicate business logic).

| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/api/v1/health` | Public | Health check |
| POST | `/api/v1/auth/login` | Public | Login with phone + password |
| GET | `/api/v1/auth/me` | Auth | Current user |
| POST | `/api/v1/users` | Admin | Register user |
| POST | `/api/v1/buildings` | Admin | Create building |
| POST | `/api/v1/subscriptions` | Admin | Create door subscription for user |
| POST | `/api/v1/chips` | Admin | Assign physical chip to user |
| DELETE | `/api/v1/chips/{id}` | Admin | Deactivate chip |
| POST | `/api/v1/chips/{id}/activate` | Admin | Activate chip |
| DELETE | `/api/v1/chips/{id}` | Admin | Deactivate chip |
| POST | `/api/v1/transactions/import` | Admin | Upload bank CSV |
| POST | `/api/v1/me/password` | Auth | Change own password |
| GET | `/api/v1/me` | User | Dashboard (profile, subs, chips, balance) |
| GET | `/api/v1/me/subscriptions` | User | Own door subscriptions |
| GET | `/api/v1/me/chips` | User | Own active/inactive chips |
| GET | `/api/v1/me/transactions` | User | Payment & fee history |

## Data model

- **User** — phone, ID number, email, role, status, account balance
- **Building** — building number, name, address
- **Subscription** — user + building + door, monthly fee, next payment due, status (billing unit)
- **Chip** — physical chip number linked to user; activate or deactivate
- **Transaction** — ledger: `payment` (+amount), `fee` (-amount)

## Balance logic

- **Payment** → increases `user.balance` (CSV import or future gateway)
- **Monthly fee (scheduler)** → subtracts `subscription.monthly_fee` from `user.balance`
- If balance goes **below 0** after a fee → subscription marked `overdue`
- Balance can be **positive or negative**

## CSV payment import (Georgian bank export)

Upload the standard TBC/BoG CSV (Georgian header row + English header row + data).

Only **Income** rows with positive amounts are processed. Each row is saved to `bank_imports` and, when matched, credited to the user's balance.

### Matching priority

1. **Building payment reference** in Description / Additional fields (highest priority), e.g. `350012A` (`building.id` + `building_number` + `door_number`, no separators)
2. **Partner's Tax Code** → user's `id_number`
3. **ID at end of Partner's Name** (e.g. `", 01010015553"`)

### What to tell customers

| Scenario | Payment description |
|----------|-------------------|
| Paying for one door | `350012A` (building id `3`, building number `500`, door `12A`) |
| Paying for multiple doors in one transfer | `350012A, 350014B` |
| No description provided | Falls back to Partner's Tax Code / Partner Name parsing |

Each subscription has a unique payment reference shown in the admin subscriptions list.

### Unmatched payments

If no user matches, the payment appears on the admin dashboard under **Unmatched**. You can assign it to an existing user or create a new user from the bank record.

`POST /api/v1/transactions/import` or **Admin → Import Payments** in the web UI.

## Background jobs

When `SCHEDULER_ENABLED=true`:

- **Daily 02:00 UTC** — process subscriptions due today: charge fee, update balance, mark overdue if needed
- **Every 30 minutes** — scheduler heartbeat

## Tests

```bash
pytest
```

## Production checklist

1. Set strong `SECRET_KEY` and `JWT_SECRET_KEY` (32+ chars)
2. Use PostgreSQL: `DATABASE_URL=postgresql://...`
3. Use Redis for rate limiting: `RATELIMIT_STORAGE_URI=redis://...`
4. Run behind HTTPS (reverse proxy)
5. Change default admin credentials immediately
6. Set `DEFAULT_PHONE_REGION=GE` and `FLASK_ENV=production`
