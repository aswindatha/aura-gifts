import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    # Database URL
    db_url = "postgresql+asyncpg://postgres:root@localhost:5432/aura_prints"
    engine = create_async_engine(db_url)
    
    async with engine.connect() as conn:
        try:
            # Query all config in ecommerce.site_config
            result = await conn.execute(text("SELECT key, value FROM ecommerce.site_config"))
            configs = result.fetchall()
            print("Found configs:")
            for config in configs:
                print(f"Key: {config[0]}, Value length: {len(str(config[1]))}")
        except Exception as e:
            print(f"Error querying config: {e}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
