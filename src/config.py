from decouple import config

# Bot
BOT_TOKEN = config('TOKEN')

# Database
DB_HOST = config('DB_HOST', default='localhost')
DB_PORT = config('DB_PORT', default=5432, cast=int)
DB_NAME = config('DB_NAME', default='payment_bot')
DB_USER = config('DB_USER', default='postgres')
DB_PASSWORD = config('DB_PASSWORD', default='postgres')

# Telegram Group
GROUP_ID = config('GROUP_ID', default=0, cast=int)

# Admin
ADMIN_IDS = list(map(int, config('ADMIN_IDS', default='').split(','))) if config('ADMIN_IDS', default='') else []

# Payment Providers
CLICK_PROVIDER_TOKEN = config('CLICKUP', default='')
PAYME_PROVIDER_TOKEN = config('PAMYE_BUSINESS', default='')

# Course Payment
COURSE_PRICE = 3_000_000  # Total course price in UZS
MONTHLY_PAYMENT = 1_000_000  # Monthly payment amount
MONTHS_COUNT = 3  # Number of monthly payments

# Scheduler
REMINDER_DAYS = [1, 3, 5]  # Days before due date to send reminders
BILLING_CHECK_HOUR = 9  # Hour to run daily billing check (24h format)
