import asyncio
import asyncpg

async def main():
    print("Connecting to database...")
    conn = await asyncpg.connect('postgresql://postgres:root@localhost:5432/aura_prints')
    try:
        async with conn.transaction():
            print("Applying schema updates to ecommerce.rfid_cards...")
            
            # Drop old unique constraints/indexes
            await conn.execute("ALTER TABLE ecommerce.rfid_cards DROP CONSTRAINT IF EXISTS rfid_cards_user_id_key")
            await conn.execute("ALTER TABLE ecommerce.rfid_cards DROP CONSTRAINT IF EXISTS rfid_cards_rfid_uid_key")
            await conn.execute("DROP INDEX IF EXISTS ecommerce.rfid_cards_user_id_key")
            await conn.execute("DROP INDEX IF EXISTS ecommerce.rfid_cards_rfid_uid_key")
            
            # Add columns
            await conn.execute("ALTER TABLE ecommerce.rfid_cards ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE")
            await conn.execute("ALTER TABLE ecommerce.rfid_cards ADD COLUMN IF NOT EXISTS deactivated_at TIMESTAMP WITH TIME ZONE")
            
            # Create partial unique indexes
            await conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_rfid_cards_active_uid 
                ON ecommerce.rfid_cards (rfid_uid) 
                WHERE (is_active = TRUE)
            """)
            await conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_rfid_cards_active_user 
                ON ecommerce.rfid_cards (user_id) 
                WHERE (is_active = TRUE)
            """)
            
            print("Creating ecommerce.rfid_scan_logs table...")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ecommerce.rfid_scan_logs (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    rfid_uid VARCHAR(255) NOT NULL,
                    user_id UUID REFERENCES ecommerce.users(id) ON DELETE SET NULL,
                    scan_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) NOT NULL,
                    scanner_id VARCHAR(100) DEFAULT 'admin_console'
                )
            """)
            
            # Indexes on scan logs
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_rfid_scan_logs_uid ON ecommerce.rfid_scan_logs(rfid_uid)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_rfid_scan_logs_user_id ON ecommerce.rfid_scan_logs(user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_rfid_scan_logs_time ON ecommerce.rfid_scan_logs(scan_time)")
            
            print("DB migration completed successfully!")
    except Exception as e:
        print(f"Error during DB migration: {e}")
        raise
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
