"""
One-time migration: SQLite glizzness.db → Supabase Postgres
Run AFTER creating the schema in the Supabase SQL Editor.
"""

import sqlite3
import os
import sys
from supabase import create_client

SUPABASE_URL = "https://ikhcbncnaojrndilmnnd.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

DB_PATH = os.path.join(os.path.dirname(__file__), "glizzness.db")

TABLES = [
    "payouts",
    "payments",
    "orders",
    "payout_entries",
    "journal_entries",
    "journal_entry_lines",
    "wave_posts",
    "wave_accounts",
    "wave_transactions",
    "loan_payments",
    "loan_journal_entries",
    "sync_log",
]

# journal_entry_lines and sync_log have SERIAL PKs — strip the SQLite autoincrement id
# so Supabase assigns its own sequence values
STRIP_ID = {"journal_entry_lines", "sync_log"}


def migrate_table(supabase, sqlite_conn, table: str):
    c = sqlite_conn.cursor()
    c.execute(f"SELECT * FROM {table}")
    cols = [d[0] for d in c.description]
    rows = c.fetchall()

    if not rows:
        print(f"  {table}: 0 rows — skipping")
        return

    records = []
    for row in rows:
        rec = dict(zip(cols, row))
        if table in STRIP_ID:
            rec.pop("id", None)
        records.append(rec)

    # Upsert in batches of 500 to stay well under Supabase limits
    BATCH = 500
    total = 0
    for i in range(0, len(records), BATCH):
        batch = records[i : i + BATCH]
        supabase.table(table).upsert(batch, on_conflict=_pk(table)).execute()
        total += len(batch)
        print(f"  {table}: {total}/{len(records)}", end="\r")

    print(f"  {table}: {len(records)} rows migrated      ")


def _pk(table: str) -> str:
    pks = {
        "payouts": "payout_id",
        "payments": "payment_id",
        "orders": "order_id",
        "payout_entries": "entry_id",
        "journal_entries": "payout_id",
        "journal_entry_lines": "id",
        "wave_posts": "payout_id",
        "wave_accounts": "account_id",
        "wave_transactions": "row_key",
        "loan_payments": "payment_date",
        "loan_journal_entries": "payment_date",
        "sync_log": "id",
    }
    return pks[table]


def main():
    if not SUPABASE_KEY:
        print("ERROR: Set SUPABASE_SERVICE_KEY environment variable")
        sys.exit(1)

    print(f"Connecting to Supabase: {SUPABASE_URL}")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    print(f"Opening SQLite: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    for table in TABLES:
        try:
            migrate_table(supabase, conn, table)
        except Exception as e:
            print(f"  ERROR on {table}: {e}")

    conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    main()
