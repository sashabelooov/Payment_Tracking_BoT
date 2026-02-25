import asyncpg
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

_pool: asyncpg.Pool | None = None


async def create_pool() -> asyncpg.Pool:
    global _pool
    _pool = await asyncpg.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        min_size=2,
        max_size=10,
    )
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized. Call create_pool() first.")
    return _pool
