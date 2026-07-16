"""Inspect offer-related tables in the database."""
import asyncio
import sys
import io
from sqlalchemy import text
from app.database import engine

# Force UTF-8 output (Windows console defaults to cp1252 and chokes on ₹)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


async def check():
    async with engine.connect() as conn:
        # 1. All offers
        r = await conn.execute(text(
            "SELECT offer_id, offer_name, status, created_at, updated_at "
            "FROM ecommerce.offers ORDER BY created_at;"
        ))
        offers = r.fetchall()
        print(f"=== OFFERS ({len(offers)}) ===")
        for o in offers:
            print(f"  {o[0]}  |  {o[1]}  |  {o[2]}  |  created={o[3]}  updated={o[4]}")

        # 2. Qualifying products
        r = await conn.execute(text(
            "SELECT q.id, q.offer_id, q.product_id, o.offer_name "
            "FROM ecommerce.offer_qualifying_products q "
            "JOIN ecommerce.offers o ON q.offer_id = o.offer_id "
            "ORDER BY q.offer_id;"
        ))
        qps = r.fetchall()
        print(f"\n=== QUALIFYING PRODUCTS ({len(qps)}) ===")
        for q in qps:
            print(f"  link={q[0]}  |  offer={q[3]}  |  product_id={q[2]}")

        # 3. Redemptions
        r = await conn.execute(text(
            "SELECT redemption_id, offer_id, customer_id, order_id, redeemed_at, benefit_applied "
            "FROM ecommerce.offer_redemptions ORDER BY redeemed_at DESC LIMIT 20;"
        ))
        reds = r.fetchall()
        print(f"\n=== REDEMPTIONS ({len(reds)}) ===")
        if not reds:
            print("  (none)")
        for rd in reds:
            print(f"  redemption={rd[0]}  |  offer={rd[1]}  |  customer={rd[2]}  |  order={rd[3]}  |  at={rd[4]}  |  benefit={rd[5]}")


if __name__ == "__main__":
    asyncio.run(check())
