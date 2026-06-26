"""
database.py — SQLAlchemy async engine & session
================================================
Automatically uses the correct engine settings depending on PRODUCTION flag:

  Dev  (PRODUCTION=0): plain asyncpg to local Postgres, no SSL, standard pool
  Prod (PRODUCTION=1): asyncpg to Supabase Transaction Pooler (PgBouncer):
                         - ssl="require"
                         - statement_cache_size=0  (required by PgBouncer)
                         - conservative pool size (PgBouncer manages the real pool)
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings
import logging

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)  # reduce noise in prod

# ─── Connection args differ per environment ───────────────────────────────────
if settings.IS_PRODUCTION:
    # Supabase Transaction Pooler requirements
    _connect_args = {
        "ssl": "require",
        "statement_cache_size": 0,           # PgBouncer transaction mode
        "prepared_statement_cache_size": 0,
    }
    _pool_kwargs = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 300,   # recycle before Supabase's idle timeout kicks in
        "pool_pre_ping": True,
    }
else:
    # Local Postgres — simple settings, no SSL required
    _connect_args = {}
    _pool_kwargs = {
        "pool_size": 5,
        "max_overflow": 5,
        "pool_pre_ping": True,
    }

# ─── Engine ───────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    echo=not settings.IS_PRODUCTION,   # echo SQL only in dev
    **_pool_kwargs,
)

# ─── Session factory ──────────────────────────────────────────────────────────
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ─── FastAPI dependency ───────────────────────────────────────────────────────
async def get_db():
    """Yield an AsyncSession per request, always closing it on exit."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
