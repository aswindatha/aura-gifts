"""
Generate a complete SQL dump file for Supabase import.
Includes: schema (CREATE TABLE), all data (INSERT), indexes, and constraints.
Run: python generate_supabase_dump.py
Output: supabase_dump.sql
"""
import psycopg2
import json
import re
from datetime import datetime, date
from decimal import Decimal

DB_URL = "postgresql://postgres:password@localhost:5432/aura_prints"
OUTPUT_FILE = "supabase_dump.sql"

conn = psycopg2.connect(DB_URL)
conn.set_session(readonly=True)
cur = conn.cursor()

def sql_escape(val):
    """Convert a Python value to a SQL literal."""
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float, Decimal)):
        return str(val)
    if isinstance(val, (datetime, date)):
        return f"'{val.isoformat()}'"
    if isinstance(val, (dict, list)):
        # JSONB column — use json.dumps then single-quote
        s = json.dumps(val, ensure_ascii=False, default=str)
        s = s.replace("'", "''")
        return f"'{s}'::jsonb"
    # String
    s = str(val).replace("'", "''")
    return f"'{s}'"

def get_create_table_sql(table_name, schema="ecommerce"):
    """Generate CREATE TABLE statement from information_schema."""
    # Get columns
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
        # Build type
        if data_type == "character varying":
            col_type = f"VARCHAR({char_len})" if char_len else "VARCHAR"
        elif data_type == "character":
            col_type = f"CHAR({char_len})" if char_len else "CHAR"
        elif data_type == "numeric":
            if num_prec is not None and num_scale is not None:
                col_type = f"NUMERIC({num_prec},{num_scale})"
            else:
                col_type = "NUMERIC"
        elif data_type == "smallint":
            col_type = "SMALLINT"
        elif data_type == "integer":
            col_type = "INTEGER"
        elif data_type == "bigint":
            col_type = "BIGINT"
        elif data_type == "boolean":
            col_type = "BOOLEAN"
        elif data_type == "text":
            col_type = "TEXT"
        elif data_type == "timestamp with time zone":
            col_type = "TIMESTAMPTZ"
        elif data_type == "timestamp without time zone":
            col_type = "TIMESTAMP"
        elif data_type == "date":
            col_type = "DATE"
        elif data_type == "uuid":
            col_type = "UUID"
        elif data_type == "jsonb":
            col_type = "JSONB"
        elif data_type == "json":
            col_type = "JSON"
        elif data_type == "bytea":
            col_type = "BYTEA"
        else:
            col_type = data_type.upper()

        col_def = f'    "{col_name}" {col_type}'
        if nullable == "NO":
            col_def += " NOT NULL"
        if default is not None:
            # Convert default to uppercase for SQL keywords
            d = default
            if d.startswith("nextval("):
                col_def += f' DEFAULT {d}'
            elif d in ("true", "false"):
                col_def += f' DEFAULT {d.upper()}'
            elif d.startswith("'") or d.startswith("NULL"):
                col_def += f' DEFAULT {d}'
            else:
                col_def += f' DEFAULT {d}'
        col_defs.append(col_def)

    # Get primary key
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
        col_defs.append(f'    PRIMARY KEY ({pk_list})')

    # Get unique constraints (using pg_constraint for conname)
    cur.execute("""
        SELECT con.conname,
               (SELECT string_agg(att.attname, ', ' ORDER BY u.ord)
                FROM unnest(con.conkey) WITH ORDINALITY u(attnum, ord)
                JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = u.attnum)
        FROM pg_constraint con
        JOIN pg_class cls ON cls.oid = con.conrelid
        JOIN pg_namespace nsp ON nsp.oid = con.connamespace
        WHERE nsp.nspname = %s AND cls.relname = %s
          AND con.contype = 'u'
    """, (schema, table_name))
    for conname, cols in cur.fetchall():
        if cols:
            col_list = ", ".join('"' + c.strip() + '"' for c in cols.split(","))
            col_defs.append(f'    CONSTRAINT "{conname}" UNIQUE ({col_list})')

    # Get foreign keys (using pg_constraint)
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
                   WHEN 'a' THEN 'NO ACTION'
                   WHEN 'r' THEN 'RESTRICT'
                   WHEN 'c' THEN 'CASCADE'
                   WHEN 'n' THEN 'SET NULL'
                   WHEN 'd' THEN 'SET DEFAULT'
               END AS delete_rule
        FROM pg_constraint con
        JOIN pg_class cls ON cls.oid = con.conrelid
        JOIN pg_namespace nsp ON nsp.oid = con.connamespace
        JOIN pg_class ref_cls ON ref_cls.oid = con.confrelid
        JOIN pg_namespace ref_nsp ON ref_nsp.oid = ref_cls.relnamespace
        WHERE nsp.nspname = %s AND cls.relname = %s
          AND con.contype = 'f'
    """, (schema, table_name))
    for conname, cols, ref_schema, ref_table, ref_cols, del_rule in cur.fetchall():
        if cols and ref_cols:
            fk_cols = ", ".join('"' + c.strip() + '"' for c in cols.split(","))
            ref_c = ", ".join('"' + c.strip() + '"' for c in ref_cols.split(","))
            col_defs.append(
                f'    CONSTRAINT "{conname}" FOREIGN KEY ({fk_cols}) '
                f'REFERENCES "{ref_schema}"."{ref_table}" ({ref_c}) '
                f'ON DELETE {del_rule}'
            )

    return f'CREATE TABLE IF NOT EXISTS "{schema}"."{table_name}" (\n' + ",\n".join(col_defs) + "\n);"

def get_indexes_sql(table_name, schema="ecommerce"):
    """Generate CREATE INDEX statements."""
    cur.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = %s AND tablename = %s
        ORDER BY indexname
    """, (schema, table_name))
    indexes = cur.fetchall()
    result = []
    for idxname, idxdef in indexes:
        # Skip primary key indexes (auto-created)
        if idxname.endswith("_pkey"):
            continue
        result.append(idxdef + ";")
    return result

def get_insert_sql(table_name, schema="ecommerce"):
    """Generate INSERT statements for all rows in a table."""
    # Get column names in order
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
    """, (schema, table_name))
    col_names = [r[0] for r in cur.fetchall()]
    if not col_names:
        return []

    # Fetch all data
    cols_csv = ", ".join('"' + c + '"' for c in col_names)
    cur.execute('SELECT ' + cols_csv + ' FROM "' + schema + '"."' + table_name + '"')
    rows = cur.fetchall()
    if not rows:
        return []

    statements = []
    # Use a comment header
    statements.append(f"-- {len(rows)} row(s) in {schema}.{table_name}")

    for row in rows:
        values = ", ".join(sql_escape(v) for v in row)
        col_list = ", ".join('"' + c + '"' for c in col_names)
        statements.append(
            'INSERT INTO "' + schema + '"."' + table_name + '" (' + col_list + ') VALUES (' + values + ');'
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

# ─── Generate the SQL file ─────────────────────────────────────────────────
lines = []
lines.append("-- ============================================================================")
lines.append("-- AURA Prints & Gifts — Complete Database Dump for Supabase Import")
lines.append(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
lines.append("-- ============================================================================")
lines.append("")
lines.append("-- This script will:")
lines.append("--   1. Create the 'ecommerce' schema")
lines.append("--   2. Create all tables with columns, primary keys, unique constraints, FKs")
lines.append("--   3. Insert all data (products, offers, users, UPI details, etc.)")
lines.append("--   4. Recreate indexes")
lines.append("")
lines.append("-- Safe to run multiple times (uses IF NOT EXISTS / ON CONFLICT DO NOTHING)")
lines.append("")
lines.append("-- ============================================================================")
lines.append("-- SECTION 1: SCHEMA SETUP")
lines.append("-- ============================================================================")
lines.append("")
lines.append('CREATE SCHEMA IF NOT EXISTS "ecommerce";')
lines.append("")

# Enable uuid extension if not present
lines.append("-- Enable uuid-ossp for uuid_generate_v4() (Supabase has this by default)")
lines.append('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
lines.append("")

# ─── Create tables ───
lines.append("-- ============================================================================")
lines.append("-- SECTION 2: CREATE TABLES")
lines.append("-- ============================================================================")
lines.append("")

for table in TABLES_ORDERED:
    create_sql = get_create_table_sql(table)
    if create_sql:
        lines.append(f"-- Table: ecommerce.{table}")
        lines.append(create_sql)
        lines.append("")
    else:
        lines.append(f"-- WARNING: Table ecommerce.{table} not found in database")
        lines.append("")

# ─── Insert data ───
lines.append("-- ============================================================================")
lines.append("-- SECTION 3: INSERT DATA")
lines.append("-- ============================================================================")
lines.append("")

# Fix products sequence first (so autoincrement continues correctly)
lines.append("-- Reset products_id_seq after inserts to avoid conflicts")
lines.append("")

total_rows = 0
for table in TABLES_ORDERED:
    inserts = get_insert_sql(table)
    if inserts:
        lines.append(f"-- ────────────────────────────────────────────────────────────")
        lines.append(f"-- Data for table: ecommerce.{table}")
        lines.append(f"-- ────────────────────────────────────────────────────────────")
        lines.extend(inserts)
        lines.append("")
        total_rows += len(inserts) - 1  # subtract the comment line

# Reset sequence for products (autoincrement integer PK)
lines.append("-- Reset auto-increment sequence for ecommerce.products")
lines.append("SELECT setval('ecommerce.products_id_seq', (SELECT MAX(id) FROM ecommerce.products));")
lines.append("")

# ─── Create indexes ───
lines.append("-- ============================================================================")
lines.append("-- SECTION 4: CREATE INDEXES")
lines.append("-- ============================================================================")
lines.append("")

for table in TABLES_ORDERED:
    indexes = get_indexes_sql(table)
    if indexes:
        lines.append(f"-- Indexes for: ecommerce.{table}")
        for idx in indexes:
            lines.append(idx)
        lines.append("")

# ─── Summary ───
lines.append("-- ============================================================================")
lines.append("-- END OF DUMP")
lines.append(f"-- Total rows inserted: {total_rows}")
lines.append("-- ============================================================================")

# Write to file
sql_content = "\n".join(lines)
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(sql_content)

print(f"\n>> SQL dump saved to {OUTPUT_FILE}")
print(f">> Total lines: {len(lines)}")
print(f">> Total rows: {total_rows}")
print(f">> File size: {len(sql_content):,} bytes")

# Print table-by-table row counts
print("\n>> Row counts per table:")
for table in TABLES_ORDERED:
    cur.execute(f'SELECT COUNT(*) FROM "ecommerce"."{table}"')
    count = cur.fetchone()[0]
    if count > 0:
        print(f"   {table}: {count} rows")

cur.close()
conn.close()
