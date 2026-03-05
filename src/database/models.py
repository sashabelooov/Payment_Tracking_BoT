from database.connection import get_pool


async def create_tables():
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                full_name VARCHAR(255) NOT NULL,
                phone VARCHAR(20) NOT NULL,
                language VARCHAR(10) NOT NULL DEFAULT 'uz',
                registered_at TIMESTAMP DEFAULT NOW(),
                next_billing_date DATE,
                payments_completed INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                amount BIGINT NOT NULL,
                payment_method VARCHAR(10) NOT NULL,
                transaction_id VARCHAR(255),
                paid_at TIMESTAMP DEFAULT NOW(),
                billing_period INTEGER NOT NULL
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                total_amount BIGINT NOT NULL,
                monthly_amount BIGINT NOT NULL,
                months_count INTEGER NOT NULL,
                group_id BIGINT,
                invite_link TEXT DEFAULT '',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS enrollments (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
                paid_amount BIGINT DEFAULT 0,
                payments_completed INTEGER DEFAULT 0,
                next_billing_date DATE,
                enrolled_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, course_id)
            );
        """)
        # Add course_id to payments if it doesn't exist yet
        await conn.execute("""
            ALTER TABLE payments ADD COLUMN IF NOT EXISTS
                course_id INTEGER REFERENCES courses(id) ON DELETE SET NULL;
        """)
        # Add description to courses if it doesn't exist yet
        await conn.execute("""
            ALTER TABLE courses ADD COLUMN IF NOT EXISTS description TEXT DEFAULT '';
        """)
        # Add group_id and invite_link to courses if they don't exist yet
        await conn.execute("""
            ALTER TABLE courses ADD COLUMN IF NOT EXISTS group_id BIGINT;
        """)
        await conn.execute("""
            ALTER TABLE courses ADD COLUMN IF NOT EXISTS invite_link TEXT DEFAULT '';
        """)
