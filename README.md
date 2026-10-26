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

Web UI: [http://localhost:5000/](http://localhost:5000/) (public site; login at `/auth/login`)

The admin account is seeded on first startup from `ADMIN_ID_NUMBER` / `ADMIN_PASSWORD` in `.env`
and logs in with that 11-digit ID number. Changing `ADMIN_PASSWORD` later does not update an
existing admin; change it from the profile page instead.

## Database migrations

The schema is managed by Flask-Migrate (Alembic) in `migrations/`. The `flask` CLI finds the app via `wsgi.py`.

- **Development:** pending migrations are applied automatically on startup (`AUTO_MIGRATE=true`).
- **Production:** run `flask db upgrade` before starting the app; it refuses to start with pending migrations.
- **Changing a model:** `flask db migrate -m "describe change"`, review the generated file, then `flask db upgrade`.
- Databases created before migrations existed are detected on startup, brought to the baseline schema, and stamped automatically.

## Web frontend (Jinja templates)

Session-based UI alongside the REST API:

| URL | Role | Pages |
|-----|------|-------|
| `/`, `/services`, `/about`, `/contact` | Public | Landing, services, about, contact form (Georgian + English) |
| `/auth/login` | Public | Login (personal ID number). Forgotten passwords: contact us, admin resets. |
| `/admin/*` | Admin | Dashboard, users, buildings, subscriptions, chips, CSV import, inquiries |
| `/dashboard/*` | User | Dashboard, how to pay, subscriptions, chips, transactions, profile, password |

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
| POST | `/api/v1/auth/login` | Public | Login with ID number + password |
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

- **Daily 02:00 UTC, and 30 seconds after startup** — charge every billing period due on or before today, update balance, mark overdue if needed. Months missed while the server was down are caught up one at a time.
- **Every 30 minutes** — scheduler heartbeat

Safety guarantees:

- Each fee has the reference `FEE-<subscription id>-<due date>`, which is unique in the database, so a period is never charged twice (even if the due date is moved back by hand).
- Only one process per machine runs the scheduler (file lock in `instance/scheduler.lock`), so gunicorn workers and the debug reloader don't multiply charges.
- Fees keep their original day of month: a subscription due on the 31st bills on Feb 28 and then on Mar 31 again.
- Balances change with a single SQL `balance = balance + amount`, so a fee and a payment arriving at the same time can't overwrite each other.

## Deleting records

Users, subscriptions, and buildings with payment history cannot be deleted; set the status to
inactive instead so the ledger stays complete. Records without any transactions (e.g. created by
mistake) can still be deleted.

## Tests

```bash
pytest
```

## Production checklist

With `FLASK_ENV=production` the app refuses to start if `SECRET_KEY` / `JWT_SECRET_KEY` are
missing, shorter than 32 characters, equal to each other, or still the example values, if
`ADMIN_PASSWORD` is the default, or if debug is on.

1. Generate secrets: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
2. Use PostgreSQL: `DATABASE_URL=postgresql://...`
3. Use Redis for rate limiting: `RATELIMIT_STORAGE_URI=redis://...`
4. Run `flask db upgrade`, then `gunicorn wsgi:app` behind nginx over HTTPS with `PROXY_FIX_X_FOR=1`
5. Keep `FLASK_DEBUG=false`; never use `python run.py` on a server
6. Set `DEFAULT_PHONE_REGION=GE` and `FLASK_ENV=production`

## Security

- All web forms carry a CSRF token (Flask-WTF); the JSON API is exempt because it uses `Authorization` headers.
- Login is rate limited per IP and per account (only failed attempts count toward the account limit).
- Changing a password or a user's status signs that user out everywhere, including API tokens.
- Content-Security-Policy forbids inline scripts: use `data-confirm="..."` on forms and
  `data-autosubmit` on fields instead of `onsubmit` / `onchange`.
