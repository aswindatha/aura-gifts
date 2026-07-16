"""
Generate a targeted SQL update file for Supabase.
Only adds MISSING tables/columns + their data.
Does NOT touch existing tables that are already in Supabase.
"""
import psycopg2
import json
from datetime import datetime

DB_URL = "postgresql://postgres:password@localhost:5432/aura_prints"
OUTPUT_FILE = "supabase_update.sql"

conn = psycopg2.connect(DB_URL)
conn.set_session(readonly=True)
cur = conn.cursor()

def sql_escape(val):
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        return str(val)
    from decimal import Decimal
    if isinstance(val, Decimal):
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

def get_create_table_sql(table_name, schema="ecommerce"):
    cur.execute("""
        SELECT column_name, data_type, character_maximum_length, numeric_precision,
               numeric_scale, is_nullable, column_default, udt_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
    """, (schema, table_name))
    columns = cur.fetchall()
    if not columns:
        return None

    col_defs = []
    for col in columns:
        col_name, data_type, char_len, num_prec, num_scale, nullable, default, udt_name = col
        if data_type == "character varying":
            col_type = f"VARCHAR({char_len})" if char_len else "VARCHAR"
        elif data_type == "numeric":
            col_type = f"NUMERIC({num_prec},{num_scale})" if num_prec is not None else "NUMERIC"
        elif data_type == "smallint":
            col_type = "SMALLINT"
        elif data_type == "integer":
            col_type = "INTEGER"
        elif data_type == "boolean":
            col_type = "BOOLEAN"
        elif data_type == "text":
            col_type = "TEXT"
        elif data_type == "timestamp with time zone":
            col_type = "TIMESTAMPTZ"
        elif data_type == "uuid":
            col_type = "UUID"
        elif data_type == "jsonb":
            col_type = "JSONB"
        else:
            col_type = data_type.upper()

        col_def = f'  "{col_name}" {col_type}'
        if nullable == "NO":
            col_def += " NOT NULL"
        if default is not None:
            d = default
            if d.startswith("nextval("):
                col_def += f' DEFAULT {d}'
            elif d in ("true", "false"):
                col_def += f' DEFAULT {d.upper()}'
            else:
                col_def += f' DEFAULT {d}'
        col_defs.append(col_def)

    # Primary key
    cur.execute("""
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = %s AND tc.table_name = %s
          AND tc.constraint_type = 'PRIMARY KEY'
        ORDER BY kcu.ordinal_position
    """, (schema, table_name))
    pk_cols = [r[0] for r in cur.fetchall()]
    if pk_cols:
        pk_list = ", ".join('"' + c + '"' for c in pk_cols)
        col_defs.append(f'  PRIMARY KEY ({pk_list})')

    # Unique constraints
    cur.execute("""
        SELECT con.conname,
               (SELECT string_agg(att.attname, ', ' ORDER BY u.ord)
                FROM unnest(con.conkey) WITH ORDINALITY u(attnum, ord)
                JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = u.attnum)
        FROM pg_constraint con
        JOIN pg_class cls ON cls.oid = con.conrelid
        JOIN pg_namespace nsp ON nsp.oid = con.connamespace
        WHERE nsp.nspname = %s AND cls.relname = %s AND con.contype = 'u'
    """, (schema, table_name))
    for conname, cols in cur.fetchall():
        if cols:
            col_list = ", ".join('"' + c.strip() + '"' for c in cols.split(","))
            col_defs.append(f'  CONSTRAINT "{conname}" UNIQUE ({col_list})')

    # Foreign keys
    cur.execute("""
        SELECT con.conname,
               (SELECT string_agg(att.attname, ', ' ORDER BY u.ord)
                FROM unnest(con.conkey) WITH ORDINALITY u(attnum, ord)
                JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = u.attnum) AS cols,
               ref_nsp.nspname AS ref_schema,
               ref_cls.relname AS ref_table,
               (SELECT string_agg(att.attname, ', ' ORDER BY u.ord)
                FROM unnest(con.confkey) WITH ORDINALITY u(attnum, ord)
                JOIN pg_attribute att ON att.attrelid = con.confrelid AND att.attnum = u.attnum) AS ref_cols,
               CASE con.confdeltype
                   WHEN 'a' THEN 'NO ACTION' WHEN 'r' THEN 'RESTRICT'
                   WHEN 'c' THEN 'CASCADE' WHEN 'n' THEN 'SET NULL'
                   WHEN 'd' THEN 'SET DEFAULT'
               END
        FROM pg_constraint con
        JOIN pg_class cls ON cls.oid = con.conrelid
        JOIN pg_namespace nsp ON nsp.oid = con.connamespace
        JOIN pg_class ref_cls ON ref_cls.oid = con.confrelid
        JOIN pg_namespace ref_nsp ON ref_nsp.oid = ref_cls.relnamespace
        WHERE nsp.nspname = %s AND cls.relname = %s AND con.contype = 'f'
    """, (schema, table_name))
    for conname, cols, ref_schema, ref_table, ref_cols, del_rule in cur.fetchall():
        if cols and ref_cols:
            fk_cols = ", ".join('"' + c.strip() + '"' for c in cols.split(","))
            ref_c = ", ".join('"' + c.strip() + '"' for c in ref_cols.split(","))
            col_defs.append(f'  CONSTRAINT "{conname}" FOREIGN KEY ({fk_cols}) REFERENCES "{ref_schema}"."{ref_table}" ({ref_c}) ON DELETE {del_rule}')

    return f'CREATE TABLE IF NOT EXISTS "{schema}"."{table_name}" (\n' + ",\n".join(col_defs) + "\n);"

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

def get_indexes_sql(table_name, schema="ecommerce"):
    cur.execute("""
        SELECT indexname, indexdef FROM pg_indexes
        WHERE schemaname = %s AND tablename = %s ORDER BY indexname
    """, (schema, table_name))
    result = []
    for idxname, idxdef in cur.fetchall():
        if idxname.endswith("_pkey"):
            continue
        result.append(idxdef + ";")
    return result

# ─── Generate targeted update SQL ──────────────────────────────────────────
lines = []
lines.append("-- ============================================================================")
lines.append("-- AURA Prints & Gifts — Targeted Supabase Update (MISSING TABLES ONLY)")
lines.append(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
lines.append("-- ============================================================================")
lines.append("")
lines.append("-- This script ONLY adds what's missing in Supabase:")
lines.append("--   1. ALTER TABLE products: ADD COLUMN sku")
lines.append("--   2. CREATE TABLE: offers, offer_qualifying_products, offer_redemptions, customer_info")
lines.append("--   3. INSERT data for the new tables only")
lines.append("--   4. UPDATE products with SKU values")
lines.append("--   5. CREATE indexes for new tables")
lines.append("")
lines.append("-- Existing tables (users, orders, products, etc.) are NOT recreated or truncated.")
lines.append("")
lines.append("-- ============================================================================")
lines.append("-- SECTION 1: ADD MISSING COLUMNS")
lines.append("-- ============================================================================")
lines.append("")
lines.append("-- Add sku column to products (if not already present)")
lines.append("ALTER TABLE \"ecommerce\".\"products\" ADD COLUMN IF NOT EXISTS \"sku\" VARCHAR(100);")
lines.append("-- Add unique constraint on sku (if not already present)")
lines.append("DO $$ BEGIN")
lines.append("  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'products_sku_key' AND conrelid = '\"ecommerce\".\"products\"'::regclass) THEN")
lines.append("    ALTER TABLE \"ecommerce\".\"products\" ADD CONSTRAINT \"products_sku_key\" UNIQUE (\"sku\");")
lines.append("  END IF;")
lines.append("EXCEPTION WHEN OTHERS THEN NULL; END $$;")
lines.append("")

# ─── Section 2: Create missing tables ───
lines.append("-- ============================================================================")
lines.append("-- SECTION 2: CREATE MISSING TABLES")
lines.append("-- ============================================================================")
lines.append("")

MISSING_TABLES = [
    "customer_info",
    "offers",
    "offer_qualifying_products",
    "offer_redemptions",
]

for table in MISSING_TABLES:
    create_sql = get_create_table_sql(table)
    if create_sql:
        lines.append(f"-- Table: ecommerce.{table}")
        lines.append(create_sql)
        lines.append("")
        # Add indexes
        indexes = get_indexes_sql(table)
        if indexes:
            for idx in indexes:
                lines.append(idx)
            lines.append("")
    else:
        lines.append(f"-- WARNING: Table ecommerce.{table} not found in local DB")
        lines.append("")

# ─── Section 3: Insert data for new tables ───
lines.append("-- ============================================================================")
lines.append("-- SECTION 3: INSERT DATA FOR NEW TABLES")
lines.append("-- ============================================================================")
lines.append("")

total_rows = 0
for table in MISSING_TABLES:
    inserts = get_insert_sql(table)
    if inserts:
        lines.append(f"-- ────────────────────────────────────────────────────────────")
        lines.append(f"-- Data for table: ecommerce.{table}")
        lines.append(f"-- ────────────────────────────────────────────────────────────")
        lines.extend(inserts)
        lines.append("")
        total_rows += len(inserts) - 1

# ─── Section 4: Update products with SKU values ───
lines.append("-- ============================================================================")
lines.append("-- SECTION 4: UPDATE PRODUCTS WITH SKU VALUES")
lines.append("-- ============================================================================")
lines.append("")

cur.execute('SELECT id, sku FROM "ecommerce"."products" WHERE sku IS NOT NULL ORDER BY id')
sku_rows = cur.fetchall()
lines.append(f"-- Updating {len(sku_rows)} products with SKU values")
for pid, sku in sku_rows:
    sku_escaped = sql_escape(sku)
    lines.append(f'UPDATE "ecommerce"."products" SET "sku" = {sku_escaped} WHERE "id" = {pid};')
lines.append("")

# ─── Summary ───
lines.append("-- ============================================================================")
lines.append(f"-- END OF UPDATE — {total_rows} rows in new tables, {len(sku_rows)} SKU updates")
lines.append("-- ============================================================================")

sql_content = "\n".join(lines)
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(sql_content)

print(f"\n>> Targeted update saved to {OUTPUT_FILE}")
print(f">> Total lines: {len(lines)}")
print(f">> New table rows: {total_rows}")
print(f">> SKU updates: {len(sku_rows)}")
print(f">> File size: {len(sql_content):,} bytes")

print("\n>> Row counts for new tables:")
for table in MISSING_TABLES:
    cur.execute(f'SELECT COUNT(*) FROM "ecommerce"."{table}"')
    print(f"   {table}: {cur.fetchone()[0]} rows")

cur.close()
conn.close()
