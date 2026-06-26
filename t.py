"""
Supabase PostgreSQL - connection test & schema/data import script.

Connection details (Transaction Pooler - port 6543):
  host:     aws-1-ap-south-1.pooler.supabase.com
  port:     6543
  database: postgres
  user:     postgres.hwqylmxwtrrsgdijnuek

Usage:
  1. Set your DB password via env var:
       $env:POSTGRES_PASSWORD = "your_password"   # PowerShell
       export POSTGRES_PASSWORD="your_password"   # bash
  2. Run:
       python t.py
"""

import os
import pathlib
import psycopg2

# ---------------------------------------------------------------------------
# Configuration  –  edit password here OR use the env var POSTGRES_PASSWORD
# ---------------------------------------------------------------------------
DB_HOST = "aws-1-ap-south-1.pooler.supabase.com"
DB_PORT = 6543
DB_NAME = "postgres"
DB_USER = "postgres.hwqylmxwtrrsgdijnuek"
DB_PASS = "AuraPrintsDb_2026_Secure"   # <-- update if changed

SCHEMA_SQL = pathlib.Path(__file__).parent / "backend" / "schema.sql"
DATA_SQL   = pathlib.Path(__file__).parent / "backend" / "data.sql"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_password() -> str:
    """Return password from env var (preferred) or the hard-coded fallback."""
    return os.getenv("POSTGRES_PASSWORD", DB_PASS)


def open_connection() -> psycopg2.extensions.connection:
    """Open and verify a PostgreSQL connection; return the live connection."""
    pw = get_password()
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=pw,
        connect_timeout=10,
    )
    with conn.cursor() as cur:
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
    print(f"[OK]  Connected!  PostgreSQL: {version}")
    return conn


def split_sql_statements(sql: str) -> list:
    """
    Split a SQL script into individual statements, correctly handling:
      - single-line comments  (-- ...)
      - block comments        (/* ... */)
      - string literals       ('...')
    """
    statements = []
    current = []
    i = 0
    n = len(sql)

    while i < n:
        ch = sql[i]

        # Single-line comment
        if ch == '-' and i + 1 < n and sql[i + 1] == '-':
            end = sql.find('\n', i)
            if end == -1:
                end = n
            current.append(sql[i:end])
            i = end

        # Block comment  /* ... */
        elif ch == '/' and i + 1 < n and sql[i + 1] == '*':
            end = sql.find('*/', i + 2)
            if end == -1:
                end = n
            else:
                end += 2
            current.append(sql[i:end])
            i = end

        # String literal
        elif ch == "'":
            end = i + 1
            while end < n:
                if sql[end] == "'" and (end + 1 < n and sql[end + 1] == "'"):
                    end += 2  # escaped quote
                elif sql[end] == "'":
                    end += 1
                    break
                else:
                    end += 1
            current.append(sql[i:end])
            i = end

        # Statement terminator
        elif ch == ';':
            stmt = ''.join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            i += 1

        else:
            current.append(ch)
            i += 1

    # Trailing statement without semicolon
    stmt = ''.join(current).strip()
    if stmt:
        statements.append(stmt)

    return statements


def apply_sql_file(conn: psycopg2.extensions.connection, path: pathlib.Path) -> None:
    """Execute every statement in *path* inside a single transaction."""
    if not path.exists():
        print(f"[WARN]  File not found, skipping: {path}")
        return

    raw = path.read_text(encoding="utf-8")
    # Split on semicolons; skip blank/comment-only chunks
    statements = split_sql_statements(raw)

    with conn.cursor() as cur:
        for stmt in statements:
            try:
                cur.execute(stmt)
            except Exception as exc:
                conn.rollback()
                print(f"[ERR]  Error in {path.name}: {exc}")
                raise
        conn.commit()

    print(f"[OK]  Applied {path.name}  ({len(statements)} statements)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  Aura Prints – Supabase DB init script")
    print("=" * 60)

    conn = open_connection()
    try:
        apply_sql_file(conn, SCHEMA_SQL)
        apply_sql_file(conn, DATA_SQL)
    finally:
        conn.close()
        print("[DONE]  Connection closed.")
