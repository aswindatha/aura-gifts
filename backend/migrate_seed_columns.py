"""
Add `sku` column to ecommerce.products and `promotion_group` column to ecommerce.offers.
Idempotent — safe to run multiple times.
"""
import psycopg2

conn = psycopg2.connect("postgresql://postgres:password@localhost:5432/aura_prints")
cur = conn.cursor()

# 1. Add sku column to products
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_schema='ecommerce' AND table_name='products' AND column_name='sku'
""")
if not cur.fetchone():
    cur.execute("ALTER TABLE ecommerce.products ADD COLUMN sku VARCHAR(100)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_products_sku ON ecommerce.products (sku) WHERE sku IS NOT NULL")
    print("Added 'sku' column to ecommerce.products")
else:
    print("'sku' column already exists on ecommerce.products")

# 2. Add promotion_group column to offers
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_schema='ecommerce' AND table_name='offers' AND column_name='promotion_group'
""")
if not cur.fetchone():
    cur.execute("ALTER TABLE ecommerce.offers ADD COLUMN promotion_group VARCHAR(100)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_offers_promo_group ON ecommerce.offers (promotion_group) WHERE promotion_group IS NOT NULL")
    print("Added 'promotion_group' column to ecommerce.offers")
else:
    print("'promotion_group' column already exists on ecommerce.offers")

conn.commit()
cur.close()
conn.close()
print("Migration complete.")
