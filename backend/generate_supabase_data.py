"""
Generate a DATA-ONLY SQL file for Supabase.
Schema already exists — this just inserts all rows.
"""
import psycopg2
import json
from datetime import datetime
from decimal import Decimal

DB_URL = "postgresql://postgres:password@localhost:5432/aura_prints"
OUTPUT_FILE = "supabase_data.sql"

conn = psycopg2.connect(DB_URL)
conn.set_session(readonly=True)
cur = conn.cursor()

def sql_escape(val):
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float, Decimal)):
        return str(val)
    from datetime import datetime as dt, date
    if isinstance(val, (dt, date)):
        return f"'{val.isoformat()}'"
    if isinstance(val, (dict, list)):
        s = json.dumps(val, ensure_ascii=False, default=str)
        s = s.replace("'", "''")
        return f"'{s}'::jsonb"
    s = str(val).replace("'", "''")
    return f"'{s}'"

def get_insert_sql(table_name, schema="ecommerce"):
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position
    """, (schema, table_name))
    col_names = [r[0] for r in cur.fetchall()]
    if not col_names:
        return []
    cols_csv = ", ".join('"' + c + '"' for c in col_names)
    cur.execute('SELECT ' + cols_csv + ' FROM "' + schema + '"."' + table_name + '"')
    rows = cur.fetchall()
    if not rows:
        return []
    statements = [f"-- {len(rows)} row(s) in {schema}.{table_name}"]
    for row in rows:
        values = ", ".join(sql_escape(v) for v in row)
        col_list = ", ".join('"' + c + '"' for c in col_names)
        statements.append(
            'INSERT INTO "' + schema + '"."' + table_name + '" (' + col_list + ') VALUES (' + values + ') ON CONFLICT DO NOTHING;'
        )
    return statements

# Tables in dependency order (parents first)
TABLES_ORDERED = [
    "users",
    "rfid_cards",
    "rfid_scan_logs",
    "otps",
    "products",
    "orders",
    "order_items",
    "chat_messages",
    "audit_logs",
    "media_files",
    "carts",
    "cart_items",
    "payments",
    "webhook_events",
    "refunds",
    "upi_details",
    "workflow_templates",
    "customer_info",
    "offers",
    "offer_qualifying_products",
    "offer_redemptions",
]

lines = []
lines.append("-- ============================================================================")
lines.append("-- AURA Prints & Gifts — DATA ONLY (for Supabase with existing schema)")
lines.append(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
lines.append("-- ============================================================================")
lines.append("")
lines.append("-- Schema already exists in Supabase. This file only inserts data.")
lines.append("-- TRUNCATE first to avoid duplicates, then INSERT all rows.")
lines.append("-- Safe to run multiple times.")
lines.append("")
lines.append("-- ============================================================================")
lines.append("-- STEP 1: CLEAR EXISTING DATA (reverse order to respect FKs)")
lines.append("-- ============================================================================")
lines.append("")
lines.append("TRUNCATE TABLE \"ecommerce\".\"offer_redemptions\", \"ecommerce\".\"offer_qualifying_products\", \"ecommerce\".\"offers\" CASCADE;")
lines.append("TRUNCATE TABLE \"ecommerce\".\"customer_info\" CASCADE;")
lines.append("TRUNCATE TABLE \"ecommerce\".\"workflow_templates\" CASCADE;")
lines.append("TRUNCATE TABLE \"ecommerce\".\"upi_details\" CASCADE;")
lines.append("TRUNCATE TABLE \"ecommerce\".\"refunds\" CASCADE;")
lines.append("TRUNCATE TABLE \"ecommerce\".\"webhook_events\" CASCADE;")
lines.append("TRUNCATE TABLE \"ecommerce\".\"payments\" CASCADE;")
lines.append("TRUNCATE TABLE \"ecommerce\".\"cart_items\", \"ecommerce\".\"carts\" CASCADE;")
lines.append("TRUNCATE TABLE \"ecommerce\".\"media_files\" CASCADE;")
lines.append("TRUNCATE TABLE \"ecommerce\".\"audit_logs\" CASCADE;")
lines.append("TRUNCATE TABLE \"ecommerce\".\"chat_messages\" CASCADE;")
lines.append("TRUNCATE TABLE \"ecommerce\".\"order_items\", \"ecommerce\".\"orders\" CASCADE;")
lines.append("TRUNCATE TABLE \"ecommerce\".\"products\" CASCADE;")
lines.append("TRUNCATE TABLE \"ecommerce\".\"otps\" CASCADE;")
lines.append("TRUNCATE TABLE \"ecommerce\".\"rfid_scan_logs\", \"ecommerce\".\"rfid_cards\" CASCADE;")
lines.append("TRUNCATE TABLE \"ecommerce\".\"users\" CASCADE;")
lines.append("")

lines.append("-- ============================================================================")
lines.append("-- STEP 2: INSERT ALL DATA")
lines.append("-- ============================================================================")
lines.append("")

total_rows = 0
for table in TABLES_ORDERED:
    inserts = get_insert_sql(table)
    if inserts:
        lines.append(f"-- ────────────────────────────────────────────────────────────")
        lines.append(f"-- {table} ({len(inserts) - 1} rows)")
        lines.append(f"-- ────────────────────────────────────────────────────────────")
        lines.extend(inserts)
        lines.append("")
        total_rows += len(inserts) - 1

lines.append("-- ============================================================================")
lines.append("-- STEP 3: RESET AUTO-INCREMENT SEQUENCE")
lines.append("-- ============================================================================")
lines.append("")
lines.append("SELECT setval('ecommerce.products_id_seq', (SELECT COALESCE(MAX(id), 1) FROM ecommerce.products));")
lines.append("SELECT setval('ecommerce.upi_details_id_seq', (SELECT COALESCE(MAX(id), 1) FROM ecommerce.upi_details));")
lines.append("")
lines.append("-- ============================================================================")
lines.append(f"-- DONE — {total_rows} rows inserted")
lines.append("-- ============================================================================")

sql_content = "\n".join(lines)
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(sql_content)

print(f"\n>> Data-only SQL saved to {OUTPUT_FILE}")
print(f">> Total lines: {len(lines)}")
print(f">> Total rows: {total_rows}")
print(f">> File size: {len(sql_content):,} bytes")

print("\n>> Row counts:")
for table in TABLES_ORDERED:
    cur.execute(f'SELECT COUNT(*) FROM "ecommerce"."{table}"')
    count = cur.fetchone()[0]
    if count > 0:
        print(f"   {table}: {count}")

cur.close()
conn.close()
