# Payment Tracking Telegram Bot

## Project Overview
Telegram bot for an offline accounting course center. Registers users, manages multiple courses, collects payments via Click/Payme (Telegram Payments API), tracks per-course billing cycles, sends reminders, exports student data to Excel, and auto-removes non-paying users from a private Telegram group.

## Tech Stack
- Python 3.11+, Aiogram 3.x (async Telegram Bot API)
- PostgreSQL + asyncpg (database)
- APScheduler (scheduled billing checks & reminders)
- python-decouple (env config)
- openpyxl (Excel export)

## Project Structure
```
src/
├── runbot.py            # Entry point — bot startup, lifecycle hooks
├── config.py            # All settings from .env + constants
├── states.py            # FSM states (UserState, AdminState)
├── keyboards.py         # All reply keyboards
├── data.json            # Multi-language translations (uz/ru)
├── handlers/            # Telegram message handlers
│   ├── __init__.py      # Router setup — registration order matters
│   ├── registration.py  # /start, language, phone, name, confirm
│   ├── main_menu.py     # Main menu + course browsing/payment
│   ├── payment.py       # Legacy payment + course payment callbacks
│   └── admin.py         # /adminpanel, users, stats, broadcast, course CRUD, Excel export, payments, admin mgmt
├── database/            # PostgreSQL layer
│   ├── __init__.py      # Re-exports pool functions
│   ├── connection.py    # asyncpg pool management
│   ├── models.py        # Table creation SQL (users, payments, courses, enrollments)
│   └── queries.py       # All CRUD operations
├── payments/            # Payment providers (Telegram Payments API)
│   ├── click.py         # Click: legacy + course invoices
│   └── payme.py         # Payme: legacy + course invoices
└── scheduler/           # Background jobs
    ├── setup.py         # APScheduler configuration
    └── tasks.py         # Reminder & expiry check logic
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
- Main admin access is controlled by `ADMIN_IDS` in `.env` (comma-separated Telegram user IDs)
- Additional admins are stored in `bot_admins` DB table (added by main admins via bot)
- Router registration order in `handlers/__init__.py`: admin > registration > main_menu > payment

## Database Schema

### Tables
- **users** — telegram_id, full_name, phone, language, registered_at, next_billing_date, payments_completed, is_active
- **payments** — user_id (FK), amount, payment_method, transaction_id, paid_at, billing_period, course_id (FK, nullable), receipt_file_id
- **courses** — title (UNIQUE), description, start_date, end_date, total_amount, monthly_amount, months_count, group_id, invite_link, is_active, created_at
- **enrollments** — user_id (FK), course_id (FK), paid_amount, payments_completed, next_billing_date, enrolled_at, UNIQUE(user_id, course_id)
- **bot_admins** — telegram_id (UNIQUE), added_by, added_at

## Payment Flow

### Legacy (hardcoded single course)
1. User: Main Menu > Payment > Make Payment > Click/Payme
2. Payload format: `"click_{chatid}_{period}"` (3 parts)
3. On success: save payment, update user billing, send group invite on first payment

### Course-based
1. User: Main Menu > Courses > Select Course > Pay > Click/Payme
2. Payload format: `"click_{chatid}_c{courseid}_{period}"` (4 parts, "c" prefix)
3. On success: save payment with course_id, auto-enroll if first payment, update enrollment billing

### Payment callback handlers in `payment.py` detect legacy vs course by payload part count.

## Admin Panel
- Access: `/adminpanel` command
- Main admins: defined in `ADMIN_IDS` in `.env` — can add/remove other admins
- DB admins: stored in `bot_admins` table — added by main admins, cannot manage other admins
- `is_admin()` checks both `.env` and database
- Features: manual payment (cash/card), user list, statistics, broadcast, create course, Excel export, kick user from group, add/remove admin (main only)
- Course creation FSM: title > description > start date > end date > months count > total amount > group_id > invite_link > confirm
- Admin payment FSM: method (cash/card) > course > phone search > amount > receipt image > confirm

## Scheduler
- Reminders sent on days 1, 3, 5 before billing due date (9:00 AM)
- Expired billing check runs daily (10:00 AM) — removes overdue users from group

## Skills Guide

### Adding a New Handler
1. Create handler file in `src/handlers/`
2. Define `router = Router()` at the top
3. Add FSM states to `states.py` if needed
4. Add button text to `data.json` (both uz and ru)
5. Add keyboard function to `keyboards.py`
6. Register router in `handlers/__init__.py` (order matters — higher priority first)

### Adding a New Database Table
1. Add `CREATE TABLE IF NOT EXISTS` in `database/models.py` inside `create_tables()`
2. Add query functions in `database/queries.py` (follow existing pattern: `get_pool() > acquire > fetchrow/fetch/execute`)
3. Import and use in handlers

### Adding a New Payment Provider
1. Create `src/payments/provider.py` with `send_provider_invoice()` and `send_provider_invoice_for_course()`
2. Add provider token to `config.py` and `.env`
3. Import in `handlers/payment.py` and add to payment method handler
4. Payload prefix must be unique (e.g., `"providername_{chatid}_{period}"`)

### Adding New Translations
1. Add key to both `"🇺🇿 uz"` and `"🇷🇺 ru"` sections in `data.json`
2. Message text goes in `message_text`, button labels go in `buttons`
3. Use `{placeholder}` syntax for dynamic values
4. Access via `get_text(lang, 'message_text', 'key_name')` or `get_text(lang, 'buttons', 'key_name')`

### Adding a New Admin Feature
1. Add new button text to `admin_menu()` in `keyboards.py`
2. Add FSM state to `AdminState` in `states.py` if needed
3. Add `elif message.text == "..."` branch in `admin_menu_handler` in `handlers/admin.py`
4. Add handler function with `@router.message(AdminState.new_state)` decorator
5. Always check `await is_admin(message.from_user.id)` at the start of each admin handler (async!)
6. Use `is_main_admin()` (sync) for features restricted to main admins only

### Adding a New Course Feature for Users
1. Add FSM state to `UserState` in `states.py`
2. Add translations to `data.json` (uz + ru)
3. Add keyboard in `keyboards.py`
4. Add handler in `handlers/main_menu.py` with proper state filter
5. For payments: use `send_*_invoice_for_course()` with 4-part payload format
