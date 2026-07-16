"""Drop and recreate offer tables to fix the order_id type mismatch."""
import asyncio
from sqlalchemy import text
from app.database import engine


async def fix():
    async with engine.begin() as conn:
        # Check what exists
        result = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'ecommerce' AND table_name LIKE 'offer%'"
        ))
        tables = [r[0] for r in result.fetchall()]
        print(f"Existing offer tables: {tables}")

        # Drop in dependency order
        for t in ["offer_redemptions", "offer_qualifying_products", "offers"]:
            if t in tables:
                print(f"Dropping ecommerce.{t}...")
                await conn.execute(text(f'DROP TABLE IF EXISTS ecommerce."{t}" CASCADE'))
        print("Done dropping. Tables will be recreated on server startup.")


asyncio.run(fix())
