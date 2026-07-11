"""
upload_site_assets.py
=====================
Uploads the AURA logo to Cloudflare R2 under site-assets/logo.jpeg
and registers the public URL in ecommerce.site_config under the key 'site_logo_url'.

Run from backend root:
    python upload_site_assets.py
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

LOGO_PATH = Path(__file__).parent.parent / "logo.jpeg"


async def upload_logo():
    # ── Resolve settings ──────────────────────────────────────────────────────
    from app.config import settings

    r2_account_id = settings.R2_ACCOUNT_ID
    r2_access_key = settings.R2_ACCESS_KEY_ID
    r2_secret_key = settings.R2_SECRET_ACCESS_KEY
    r2_bucket = settings.R2_BUCKET_NAME
    r2_domain = settings.R2_PUBLIC_CUSTOM_DOMAIN

    is_mock = not r2_access_key or not r2_secret_key or not r2_account_id or "your_r2" in r2_access_key

    r2_key = "site-assets/logo.jpeg"

    if not LOGO_PATH.exists():
        print(f"[ERROR] Logo not found at {LOGO_PATH}")
        sys.exit(1)

    logo_bytes = LOGO_PATH.read_bytes()
    print(f"[INFO] Logo size: {len(logo_bytes)} bytes")

    if is_mock:
        # Dev fallback: save locally
        local_path = Path("uploads") / r2_key
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(logo_bytes)
        public_url = f"{settings.BACKEND_URL}/static/uploads/{r2_key}"
        print(f"[DEV] Logo saved locally at: {local_path}")
    else:
        import boto3
        from botocore.config import Config

        r2_endpoint = f"https://{r2_account_id}.r2.cloudflarestorage.com"
        s3 = boto3.client(
            "s3",
            endpoint_url=r2_endpoint,
            aws_access_key_id=r2_access_key,
            aws_secret_access_key=r2_secret_key,
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )
        s3.put_object(
            Bucket=r2_bucket,
            Key=r2_key,
            Body=logo_bytes,
            ContentType="image/jpeg",
        )
        if r2_domain:
            public_url = f"{r2_domain.rstrip('/')}/{r2_key}"
        else:
            public_url = f"{r2_endpoint}/{r2_bucket}/{r2_key}"
        print(f"[R2] Logo uploaded. Public URL: {public_url}")

    # ── Store in site_config ──────────────────────────────────────────────────
    import asyncpg
    import json

    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(
            """
            INSERT INTO ecommerce.site_config (key, value, updated_at)
            VALUES ($1, $2::jsonb, NOW())
            ON CONFLICT (key) DO UPDATE
              SET value = EXCLUDED.value,
                  updated_at = NOW()
            """,
            "site_logo_url",
            json.dumps(public_url),
        )
        print(f"[DB] site_config key 'site_logo_url' set to: {public_url}")
    finally:
        await conn.close()

    print("\n✅ Done! Logo is live at:")
    print(f"   {public_url}")
    print("\nFrontend will fetch this URL via GET /api/config/site_logo_url")


if __name__ == "__main__":
    asyncio.run(upload_logo())
