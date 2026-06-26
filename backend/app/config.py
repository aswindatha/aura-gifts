"""
config.py — Aura Prints Backend Settings
=========================================
Reads PRODUCTION from .env:
  PRODUCTION=0  →  Dev mode  (local Postgres, local disk storage)
  PRODUCTION=1  →  Prod mode (Supabase, Cloudflare R2, Cloud Run)

All variable names use DEV_ / PROD_ prefixes in .env.
Universal variables (JWT, OTP, Resend) have no prefix — used in both modes.
"""

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env early so os.getenv works before pydantic reads the file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# ─── Read the master switch ───────────────────────────────────────────────────
IS_PRODUCTION: bool = os.getenv("PRODUCTION", "0").strip() == "1"
ENV_LABEL: str = "PRODUCTION" if IS_PRODUCTION else "DEVELOPMENT"


class Settings(BaseSettings):
    # ── Master switch ──────────────────────────────────────────────────────────
    PRODUCTION: int = 0           # 0 = dev, 1 = prod
    IS_PRODUCTION: bool = IS_PRODUCTION
    ENV_LABEL: str = ENV_LABEL

    # ── Database ───────────────────────────────────────────────────────────────
    # Active URL is resolved below after instantiation.
    DEV_DATABASE_URL: str  = "postgresql+asyncpg://postgres:root@localhost:5432/aura_prints"
    PROD_DATABASE_URL: str = "postgresql+asyncpg://postgres.hwqylmxwtrrsgdijnuek:AuraPrintsDb_2026_Secure@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"
    DATABASE_URL: str = ""
    BACKEND_URL: str = ""

    # ── Backend URLs ───────────────────────────────────────────────────────────
    DEV_BACKEND_URL: str  = "http://localhost:8000"
    PROD_BACKEND_URL: str = "https://your-cloudrun-service-url.run.app"

    # ── Storage (dev = local disk served by FastAPI) ───────────────────────────
    DEV_STORAGE_BASE_URL: str = "http://localhost:8000/uploads"

    # ── Cloudflare R2 (prod only) ──────────────────────────────────────────────
    PROD_R2_ACCOUNT_ID: str           = ""
    PROD_R2_ACCESS_KEY_ID: str        = ""
    PROD_R2_SECRET_ACCESS_KEY: str    = ""
    PROD_R2_BUCKET_NAME: str          = "aura-prints"
    PROD_R2_PUBLIC_CUSTOM_DOMAIN: str = ""
    # ── Runtime R2 fields (populated based on environment) ───────────────────────
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = ""
    R2_PUBLIC_CUSTOM_DOMAIN: str = ""
    STORAGE_BASE_URL: str = ""

    # ── Universal / Common ─────────────────────────────────────────────────────
    JWT_SECRET_KEY: str       = "aura-prints-development-secret-key-replace-in-production"
    JWT_ALGORITHM: str        = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    OTP_HMAC_SECRET: str      = ""
    OTP_EXPIRE_MINUTES: int   = 10

    RESEND_API_KEY: str       = ""
    CRON_SECRET_KEY: str      = "aura-prints-default-cron-secret-key-change-in-production"

    # ── Chat ───────────────────────────────────────────────────────────────────
    CHAT_RETENTION_DAYS: int      = 30
    CHAT_MESSAGE_LIMIT: int       = 500
    CHAT_MAX_LENGTH: int          = 1000
    CHAT_RATE_LIMIT_SECONDS: int  = 5
    CHAT_ALLOWED_STATUSES: list[int] = [1, 2, 3, 4, 5, 6, 7]

    class Config:
        env_file = ".env"
        extra = "ignore"


# ─── Instantiate ──────────────────────────────────────────────────────────────
settings = Settings()

# ─── Resolve active values based on PRODUCTION flag ──────────────────────────
settings.DATABASE_URL = (
    settings.PROD_DATABASE_URL if IS_PRODUCTION else settings.DEV_DATABASE_URL
)
settings.BACKEND_URL = (
    settings.PROD_BACKEND_URL if IS_PRODUCTION else settings.DEV_BACKEND_URL
)

# Storage / R2 — expose a flat set of names the rest of the app uses
if IS_PRODUCTION:
    settings.R2_ACCOUNT_ID           = settings.PROD_R2_ACCOUNT_ID
    settings.R2_ACCESS_KEY_ID        = settings.PROD_R2_ACCESS_KEY_ID
    settings.R2_SECRET_ACCESS_KEY    = settings.PROD_R2_SECRET_ACCESS_KEY
    settings.R2_BUCKET_NAME          = settings.PROD_R2_BUCKET_NAME
    settings.R2_PUBLIC_CUSTOM_DOMAIN = settings.PROD_R2_PUBLIC_CUSTOM_DOMAIN
    settings.STORAGE_BASE_URL        = settings.PROD_R2_PUBLIC_CUSTOM_DOMAIN
else:
    # Dev: R2 fields are empty — storage router uses local /uploads dir instead
    settings.R2_ACCOUNT_ID           = ""
    settings.R2_ACCESS_KEY_ID        = ""
    settings.R2_SECRET_ACCESS_KEY    = ""
    settings.R2_BUCKET_NAME          = "aura-prints-local"
    settings.R2_PUBLIC_CUSTOM_DOMAIN = ""
    settings.STORAGE_BASE_URL        = settings.DEV_STORAGE_BASE_URL

# ─── Start-up banner ─────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  Aura Prints Backend  |  Mode: {ENV_LABEL}")
print(f"  DB  : {settings.DATABASE_URL.split('@')[-1]}")   # hide credentials
print(f"  Store: {settings.STORAGE_BASE_URL or 'R2 (no public domain set)'}")
print(f"{'='*60}\n")

# ─── Guard: OTP secret must always be set ────────────────────────────────────
if not settings.OTP_HMAC_SECRET:
    raise RuntimeError(
        "OTP_HMAC_SECRET is not set in .env. "
        "Please configure it before starting the application."
    )
