import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect(
        host="aws-1-ap-south-1.pooler.supabase.com",
        port=6543,
        database="postgres",
        user="postgres.hwqylmxwtrrsgdijnuek",
        password="AuraPrintsDb_2026_Secure",
        ssl="require",
        statement_cache_size=0,
    )
    row = await conn.fetchrow("SELECT version()")
    print("[OK] Connected:", row[0])

    schemas = await conn.fetch(
        "SELECT schema_name FROM information_schema.schemata "
        "WHERE schema_name IN ('ecommerce', 'maintenance')"
    )
    print("[OK] Schemas:", [r["schema_name"] for r in schemas])

    tables = await conn.fetch(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'ecommerce' ORDER BY table_name"
    )
    print("[OK] Tables in ecommerce:", [r["table_name"] for r in tables])

    await conn.close()
    print("[DONE] Connection closed.")

asyncio.run(test())
