from datetime import date, timedelta
from database.connection import get_pool


async def create_user(telegram_id: int, full_name: str, phone: str, language: str) -> dict:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO users (telegram_id, full_name, phone, language)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (telegram_id) DO UPDATE
                SET full_name = $2, phone = $3, language = $4, is_active = TRUE
            RETURNING *
            """,
            telegram_id, full_name, phone, language,
        )
        return dict(row)


async def get_user(telegram_id: int) -> dict | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1", telegram_id
        )
        return dict(row) if row else None


async def get_all_users(active_only: bool = True) -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        if active_only:
            rows = await conn.fetch("SELECT * FROM users WHERE is_active = TRUE ORDER BY id")
        else:
            rows = await conn.fetch("SELECT * FROM users ORDER BY id")
        return [dict(r) for r in rows]


async def update_user_billing(telegram_id: int, next_billing_date: date, payments_completed: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE users SET next_billing_date = $2, payments_completed = $3
            WHERE telegram_id = $1
            """,
            telegram_id, next_billing_date, payments_completed,
        )


async def deactivate_user(telegram_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_active = FALSE WHERE telegram_id = $1",
            telegram_id,
        )


async def create_payment(user_id: int, amount: int, payment_method: str,
                         transaction_id: str, billing_period: int) -> dict:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO payments (user_id, amount, payment_method, transaction_id, billing_period)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            user_id, amount, payment_method, transaction_id, billing_period,
        )
        return dict(row)


async def get_user_payments(telegram_id: int) -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT p.* FROM payments p
            JOIN users u ON u.id = p.user_id
            WHERE u.telegram_id = $1
            ORDER BY p.paid_at DESC
            """,
            telegram_id,
        )
        return [dict(r) for r in rows]


async def get_last_payment(telegram_id: int) -> dict | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT p.* FROM payments p
            JOIN users u ON u.id = p.user_id
            WHERE u.telegram_id = $1
            ORDER BY p.paid_at DESC LIMIT 1
            """,
            telegram_id,
        )
        return dict(row) if row else None


async def get_users_with_upcoming_billing(days_before: int) -> list[dict]:
    """Get users whose billing is due in exactly `days_before` days."""
    pool = get_pool()
    target_date = date.today() + timedelta(days=days_before)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM users
            WHERE is_active = TRUE
              AND next_billing_date = $1
              AND payments_completed < 3
            """,
            target_date,
        )
        return [dict(r) for r in rows]


async def get_users_with_expired_billing() -> list[dict]:
    """Get active users whose billing date has passed."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM users
            WHERE is_active = TRUE
              AND next_billing_date < $1
              AND payments_completed < 3
            """,
            date.today(),
        )
        return [dict(r) for r in rows]


# --- Course queries ---


async def create_course(title: str, start_date, end_date,
                        total_amount: int, monthly_amount: int, months_count: int) -> dict:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO courses (title, start_date, end_date, total_amount, monthly_amount, months_count)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            title, start_date, end_date, total_amount, monthly_amount, months_count,
        )
        return dict(row)


async def get_active_courses() -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM courses WHERE is_active = TRUE ORDER BY start_date"
        )
        return [dict(r) for r in rows]


async def get_course(course_id: int) -> dict | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM courses WHERE id = $1", course_id)
        return dict(row) if row else None


async def get_all_courses() -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM courses ORDER BY created_at DESC")
        return [dict(r) for r in rows]


# --- Enrollment queries ---


async def enroll_user(user_id: int, course_id: int, next_billing_date) -> dict:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO enrollments (user_id, course_id, next_billing_date)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, course_id) DO NOTHING
            RETURNING *
            """,
            user_id, course_id, next_billing_date,
        )
        if row:
            return dict(row)
        # Already enrolled, return existing
        row = await conn.fetchrow(
            "SELECT * FROM enrollments WHERE user_id = $1 AND course_id = $2",
            user_id, course_id,
        )
        return dict(row)


async def get_user_enrollment_by_telegram(telegram_id: int, course_id: int) -> dict | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT e.* FROM enrollments e
            JOIN users u ON u.id = e.user_id
            WHERE u.telegram_id = $1 AND e.course_id = $2
            """,
            telegram_id, course_id,
        )
        return dict(row) if row else None


async def update_enrollment_billing(enrollment_id: int, paid_amount: int,
                                     payments_completed: int, next_billing_date):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE enrollments
            SET paid_amount = $2, payments_completed = $3, next_billing_date = $4
            WHERE id = $1
            """,
            enrollment_id, paid_amount, payments_completed, next_billing_date,
        )


async def create_payment_for_course(user_id: int, amount: int, payment_method: str,
                                     transaction_id: str, billing_period: int,
                                     course_id: int) -> dict:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO payments (user_id, amount, payment_method, transaction_id,
                                  billing_period, course_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            user_id, amount, payment_method, transaction_id, billing_period, course_id,
        )
        return dict(row)


async def get_course_enrollments_with_users(course_id: int) -> list[dict]:
    """Get all enrollments for a course with user info (for Excel export)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT u.full_name, u.phone, u.telegram_id,
                   e.paid_amount, e.payments_completed, e.next_billing_date, e.enrolled_at,
                   c.total_amount, c.months_count, c.monthly_amount
            FROM enrollments e
            JOIN users u ON u.id = e.user_id
            JOIN courses c ON c.id = e.course_id
            WHERE e.course_id = $1
            ORDER BY u.full_name
            """,
            course_id,
        )
        return [dict(r) for r in rows]


async def get_payment_stats() -> dict:
    """Get overall payment statistics for admin panel."""
    pool = get_pool()
    async with pool.acquire() as conn:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
        total_payments = await conn.fetchval("SELECT COALESCE(SUM(amount), 0) FROM payments")
        overdue = await conn.fetchval(
            """
            SELECT COUNT(*) FROM users
            WHERE is_active = TRUE AND next_billing_date < $1 AND payments_completed < 3
            """,
            date.today(),
        )
        return {
            "total_active_users": total_users,
            "total_payments_collected": total_payments,
            "overdue_users": overdue,
        }
