import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    # Database URL
    db_url = "postgresql+asyncpg://postgres:root@localhost:5432/aura_prints"
    engine = create_async_engine(db_url)
    
    async with engine.connect() as conn:
        try:
            # Query all users in ecommerce.users
            result = await conn.execute(text("SELECT id, name, email, role FROM ecommerce.users"))
            users = result.fetchall()
            print("Found users:")
            for user in users:
                print(f"ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Role: {user[3]}")
        except Exception as e:
            print(f"Error querying users: {e}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
