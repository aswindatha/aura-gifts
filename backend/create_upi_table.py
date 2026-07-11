import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

async def main():
    # Load database url and convert postgresql+asyncpg to postgresql
    production = os.getenv("PRODUCTION", "0") == "1"
    db_url = os.getenv("PROD_DATABASE_URL") if production else os.getenv("DEV_DATABASE_URL")
    
    if not db_url:
        db_url = "postgresql://postgres:root@localhost:5432/aura_prints"
        
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    print(f"Connecting to database at {db_url}...")
    
    conn = await asyncpg.connect(db_url)
    try:
        async with conn.transaction():
            print("Creating ecommerce.upi_details table...")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ecommerce.upi_details (
                    id SERIAL PRIMARY KEY,
                    upi_id VARCHAR(255) NOT NULL,
                    upi_url TEXT NOT NULL,
                    qr_url TEXT NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Check if there is already an entry
            row_count = await conn.fetchval("SELECT COUNT(*) FROM ecommerce.upi_details;")
            if row_count == 0:
                print("Seeding default UPI record...")
                default_upi_id = "aswindathas@ibl"
                default_url = f"upi://pay?pa={default_upi_id}&pn=AURA_PRINTS&am=1.00&cu=INR&tn=test_payment_from_admin"
                # Mock QR Code URL
                default_qr_url = "https://pub-3311c02cc7624d7fa550e7962fd81c46.r2.dev/banners/default_qr.png"
                await conn.execute(
                    "INSERT INTO ecommerce.upi_details (upi_id, upi_url, qr_url) VALUES ($1, $2, $3);",
                    default_upi_id, default_url, default_qr_url
                )
            
            print("UPI Table migration completed successfully!")
    except Exception as e:
        print(f"Error during UPI Table migration: {e}")
        raise
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
