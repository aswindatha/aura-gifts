import psycopg2
import json

conn = psycopg2.connect("postgresql://postgres:password@localhost:5432/aura_prints")
cur = conn.cursor()

cur.execute("SELECT id, name, category, price FROM ecommerce.products ORDER BY id")
rows = cur.fetchall()
print(f'Total products: {len(rows)}')
for row in rows:
    print(f'  id={row[0]} | cat={row[2]} | price={row[3]} | name={row[1][:50]}')

print('---')
cur.execute("""SELECT column_name, data_type FROM information_schema.columns 
    WHERE table_schema='ecommerce' AND table_name='products' ORDER BY ordinal_position""")
print('Products columns:')
for c in cur.fetchall():
    print(f'  {c[0]}: {c[1]}')

print('---')
cur.execute("""SELECT column_name, data_type FROM information_schema.columns 
    WHERE table_schema='ecommerce' AND table_name='offers' ORDER BY ordinal_position""")
print('Offers columns:')
for c in cur.fetchall():
    print(f'  {c[0]}: {c[1]}')

print('---')
cur.execute("SELECT offer_id, offer_name, criteria_type, product_scope, status FROM ecommerce.offers ORDER BY offer_name")
rows = cur.fetchall()
print(f'Total offers: {len(rows)}')
for row in rows:
    print(f'  {row[1]} | {row[2]} | {row[3]} | {row[4]}')

cur.close()
conn.close()
