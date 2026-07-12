import asyncio
from app.database import engine
from sqlalchemy import text
async def run():
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT email_verified FROM ecommerce.users WHERE email='deva@auraprints.com'"))
        print(res.fetchall())
asyncio.run(run())

