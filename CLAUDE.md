# Payment Tracking Telegram Bot

## Project Overview
Telegram bot for an offline accounting course. Registers users, collects payments via Click/Payme, tracks billing cycles (3 months x 1,000,000 UZS), sends reminders, and auto-removes non-paying users from a private Telegram group.

## Tech Stack
- Python 3.11+, Aiogram 3.x (async Telegram Bot API)
- PostgreSQL + asyncpg (database)
- APScheduler (scheduled billing checks & reminders)
- python-decouple (env config)

## Project Structure
```
src/
├── runbot.py           # Entry point — bot startup, lifecycle hooks
├── config.py           # All settings from .env + constants
├── states.py           # FSM states (UserState, AdminState)
├── keyboards.py        # All reply keyboards
├── data.json           # Multi-language translations (uz/ru)
├── handlers/           # Telegram message handlers
│   ├── registration.py # /start, language, phone, name, confirm
│   ├── main_menu.py    # Payment, My Info, About, Contact
│   ├── payment.py      # Make payment, last billing, Click/Payme
│   └── admin.py        # /admin, user list, stats, broadcast
├── database/           # PostgreSQL layer
│   ├── connection.py   # asyncpg pool management
│   ├── models.py       # Table creation SQL
│   └── queries.py      # All CRUD operations
├── payments/           # Payment provider stubs
│   ├── click.py        # Click integration (not yet implemented)
│   └── payme.py        # Payme integration (not yet implemented)
└── scheduler/          # Background jobs
    ├── tasks.py        # Reminder & expiry check logic
    └── setup.py        # APScheduler configuration
```

## Running the Bot
```bash
cd src
pip install -r requirements.txt
# Ensure PostgreSQL is running and .env is configured
python runbot.py
```

## Key Conventions
- All user-facing text is in `data.json` (supports uz/ru)
- Use `get_text(lang, category, key)` for translations
- Database queries go in `database/queries.py` — never write raw SQL in handlers
- FSM states are in `states.py` — each handler file filters by its states
- Keyboards are in `keyboards.py` — one function per keyboard
- Bot token and secrets are in `.env` — never hardcode

## Payment Flow
1. User clicks "Make Payment" → selects Click or Payme
2. Currently uses stubs (simulates success). Replace with real API when credentials are ready.
3. On success: save payment to DB, update billing date, send group invite (first payment only)

## Scheduler
- Reminders sent on days 1, 3, 5 before billing due date (9:00 AM)
- Expired billing check runs daily (10:00 AM) — removes overdue users from group
