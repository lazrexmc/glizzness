#!/usr/bin/env python3
"""
sync_wave.py — Sync Wave data into glizzness.db.

Wave's public API does not support reading transactions — it is write-only
for accounting entries. Transactions must be imported from Wave's CSV export.

Commands:
  python sync_wave.py --sync-accounts          # pull chart of accounts from Wave API
  python sync_wave.py --import-csv <file.csv>  # import a Wave transactions CSV export
  python sync_wave.py --status                 # row counts / date ranges in DB
  python sync_wave.py --list [prefix] [N]      # browse imported transactions
                                               # prefix: "2025", "2025-10", "2026-06-08"

How to get the Wave CSV:
  Wave → Accounting → Transactions → Export (top right) → Transactions CSV
  Then: python sync_wave.py --import-csv "transactions.csv"
"""

import os
import sys
import csv
import json
import sqlite3
import requests
from datetime import datetime, timezone

WAVE_TOKEN       = os.environ.get("WAVE_TOKEN", "")
WAVE_BUSINESS_ID = os.environ.get("WAVE_BUSINESS_ID", "")

WAVE_GQL = "https://gql.waveapps.com/graphql/public"
WAVE_HEADERS = {
    "Authorization": f"Bearer {WAVE_TOKEN}",
    "Content-Type": "application/json",
}

DB_PATH = "glizzness.db"


# ── GraphQL ───────────────────────────────────────────────────────────────────

QUERY_ACCOUNTS = """
query ($businessId: ID!) {
  business(id: $businessId) {
    accounts(page: 1, pageSize: 200) {
      edges {
        node {
          id
          name
          description
          displayId
          type    { name value }
          subtype { name value }
          isArchived
          normalBalanceType
          currency { code }
        }
      }
    }
  }
}
"""


def wave_gql(query: str, variables: dict) -> dict:
    resp = requests.post(
        WAVE_GQL,
        headers=WAVE_HEADERS,
        json={"query": query, "variables": variables},
    )
    if not resp.ok:
        print(f"  [Wave HTTP {resp.status_code}] {resp.text[:600]}")
        resp.raise_for_status()
    return resp.json()


# ── Database ──────────────────────────────────────────────────────────────────

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS wave_accounts (
        account_id      TEXT PRIMARY KEY,
        name            TEXT,
        description     TEXT,
        display_id      TEXT,
        type_name       TEXT,
        type_value      TEXT,
        subtype_name    TEXT,
        subtype_value   TEXT,
        normal_balance  TEXT,
        is_archived     INTEGER,
        currency        TEXT,
        synced_at       TEXT
    );

    -- Imported from Wave CSV export (Accounting → Transactions → Export)
    CREATE TABLE IF NOT EXISTS wave_transactions (
        row_key         TEXT PRIMARY KEY,   -- date|description|account|amount deduplication key
        txn_date        TEXT,
        description     TEXT,
        account_name    TEXT,
        debit           REAL,
        credit          REAL,
        balance         REAL,
        -- Derived
        direction       TEXT,               -- DEBIT or CREDIT
        net_amount      REAL,               -- positive = credit, negative = debit
        imported_at     TEXT,
        source_file     TEXT
    );
    """)

    # Migration: add source_file if missing (idempotent)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(wave_transactions)").fetchall()]
    if "source_file" not in cols:
        conn.execute("ALTER TABLE wave_transactions ADD COLUMN source_file TEXT")

    conn.commit()


# ── Sync accounts ─────────────────────────────────────────────────────────────

def sync_accounts(conn: sqlite3.Connection) -> int:
    if not WAVE_TOKEN or not WAVE_BUSINESS_ID:
        print("[error] Set WAVE_TOKEN and WAVE_BUSINESS_ID env vars first.")
        return 0

    print("  Fetching Wave chart of accounts...")
    result = wave_gql(QUERY_ACCOUNTS, {"businessId": WAVE_BUSINESS_ID})

    if result.get("errors"):
        print(f"  [GraphQL error] {json.dumps(result['errors'])[:400]}")
        return 0

    edges = (
        (result.get("data") or {})
        .get("business", {})
        .get("accounts", {})
        .get("edges") or []
    )

    now = datetime.now(timezone.utc).isoformat()
    count = 0
    for edge in edges:
        node = edge.get("node") or {}
        conn.execute("""
            INSERT OR REPLACE INTO wave_accounts
                (account_id, name, description, display_id,
                 type_name, type_value, subtype_name, subtype_value,
                 normal_balance, is_archived, currency, synced_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            node.get("id", ""),
            node.get("name", ""),
            node.get("description", ""),
            node.get("displayId", ""),
            (node.get("type") or {}).get("name", ""),
            (node.get("type") or {}).get("value", ""),
            (node.get("subtype") or {}).get("name", ""),
            (node.get("subtype") or {}).get("value", ""),
            node.get("normalBalanceType", ""),
            1 if node.get("isArchived") else 0,
            (node.get("currency") or {}).get("code", ""),
            now,
        ))
        count += 1

    conn.commit()
    return count


# ── Import CSV ────────────────────────────────────────────────────────────────
# Wave CSV export columns (Accounting → Transactions → Export):
#   Transaction Date, Description, Debit, Credit, Balance, Account Name
# Some Wave exports use slightly different column headers — we handle variants.

def _parse_amount(val: str) -> float:
    """Strip currency symbols, commas, parentheses → float."""
    if not val or not val.strip():
        return 0.0
    v = val.strip().replace(",", "").replace("$", "").replace("(", "-").replace(")", "")
    try:
        return float(v)
    except ValueError:
        return 0.0


def _looks_like_date(val: str) -> bool:
    """Return True if val looks like YYYY-MM-DD."""
    import re
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", val.strip()))


def import_csv(conn: sqlite3.Connection, csv_path: str) -> int:
    """
    Import Wave 'Account Transactions' CSV export.

    Wave's CSV format:
      Row 1:  "Account Transactions"  (title — skip)
      Row 2:  Business name           (skip)
      Row 3:  Date range              (skip)
      Row 4:  Report type             (skip)
      Row 5:  Column headers: ACCOUNT NUMBER, DATE, DESCRIPTION,
                              DEBIT (In Business Currency),
                              CREDIT (In Business Currency),
                              BALANCE (In Business Currency)
      Then data rows — account name rows have the account name in the DATE
      column with no actual date; transaction rows have YYYY-MM-DD in DATE.
    """
    if not os.path.exists(csv_path):
        print(f"  [error] File not found: {csv_path}")
        return 0

    now    = datetime.now(timezone.utc).isoformat()
    source = os.path.basename(csv_path)
    inserted = skipped = 0
    current_account = ""

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        # Skip 4 metadata rows, then read real header
        for _ in range(4):
            f.readline()

        reader = csv.DictReader(f)

        # Map actual column names (case/space insensitive) to keys we use
        raw_headers = reader.fieldnames or []
        col = {}
        for h in raw_headers:
            hl = h.lower().strip()
            if hl == "account number":
                col["acct_num"] = h
            elif hl == "date":
                col["date"] = h
            elif hl == "description":
                col["desc"] = h
            elif "debit" in hl:
                col["debit"] = h
            elif "credit" in hl:
                col["credit"] = h
            elif "balance" in hl:
                col["balance"] = h

        missing = [k for k in ("date", "desc", "debit", "credit") if k not in col]
        if missing:
            print(f"  [error] Could not map columns: {missing}")
            print(f"  Found headers: {raw_headers}")
            return 0

        for row in reader:
            acct_num    = (row.get(col.get("acct_num", "")) or "").strip()
            date_cell   = (row.get(col.get("date", ""))     or "").strip()
            description = (row.get(col.get("desc", ""))     or "").strip()
            debit       = _parse_amount(row.get(col.get("debit",    "")) or "")
            credit      = _parse_amount(row.get(col.get("credit",   "")) or "")
            balance     = _parse_amount(row.get(col.get("balance",  "")) or "")

            # Account name row: DATE column holds account name, not a real date
            if date_cell and not _looks_like_date(date_cell):
                current_account = date_cell
                continue

            # Skip non-transaction rows (Starting Balance, totals, blanks)
            if not _looks_like_date(date_cell):
                continue
            if acct_num.lower() in ("starting balance", "ending balance", "total"):
                continue

            txn_date = date_cell

            net       = credit - debit
            direction = "CREDIT" if credit > 0 else "DEBIT"
            row_key   = f"{txn_date}|{description}|{current_account}|{debit:.2f}|{credit:.2f}"

            if conn.execute(
                "SELECT 1 FROM wave_transactions WHERE row_key = ?", (row_key,)
            ).fetchone():
                skipped += 1
                continue

            conn.execute("""
                INSERT INTO wave_transactions
                    (row_key, txn_date, description, account_name,
                     debit, credit, balance, direction, net_amount,
                     imported_at, source_file)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                row_key, txn_date, description, current_account,
                debit, credit, balance, direction, net,
                now, source,
            ))
            inserted += 1

    conn.commit()
    print(f"  Imported {inserted} rows, skipped {skipped} duplicates  ({source})")
    return inserted


# ── Status / List ─────────────────────────────────────────────────────────────

def print_status(conn: sqlite3.Connection) -> None:
    # Accounts
    n = conn.execute("SELECT COUNT(*) FROM wave_accounts").fetchone()[0]
    print(f"\n  wave_accounts:      {n} rows")
    if n:
        for r in conn.execute("""
            SELECT type_value, COUNT(*) FROM wave_accounts
            WHERE is_archived = 0
            GROUP BY type_value ORDER BY type_value
        """).fetchall():
            print(f"    {r[0]:<20} {r[1]} accounts")

    # Transactions
    row = conn.execute("""
        SELECT COUNT(*), MIN(txn_date), MAX(txn_date)
        FROM wave_transactions
    """).fetchone()
    print(f"\n  wave_transactions:  {row[0]} rows  "
          + (f"({row[1]} to {row[2]})" if row[0] else "(empty)"))
    if row[0]:
        print("\n  By year:")
        for r in conn.execute("""
            SELECT substr(txn_date,1,4) yr, COUNT(*),
                   SUM(credit) total_cr, SUM(debit) total_dr
            FROM wave_transactions
            GROUP BY yr ORDER BY yr
        """).fetchall():
            print(f"    {r[0]}   {r[1]:>5} rows   "
                  f"credits=${r[2]:>12,.2f}   debits=${r[3]:>12,.2f}")


def print_list(conn: sqlite3.Connection, prefix: str = "", limit: int = 30) -> None:
    where  = "WHERE txn_date LIKE ?" if prefix else ""
    params = [prefix + "%"] if prefix else []

    rows = conn.execute(f"""
        SELECT txn_date, description, account_name, direction,
               credit, debit, balance
        FROM wave_transactions
        {where}
        ORDER BY txn_date DESC, description
        LIMIT ?
    """, (*params, limit)).fetchall()

    if not rows:
        print(f"  No transactions{' for ' + prefix if prefix else ''}.")
        return

    print(f"\n  {'Date':<12} {'Description':<38} {'Account':<28} "
          f"{'Dir':<7} {'Amount':>10} {'Balance':>12}")
    print("  " + "-" * 112)
    for r in rows:
        amt = r[4] if r[3] == "CREDIT" else -r[5]
        print(f"  {r[0]:<12} {(r[1] or '')[:37]:<38} {(r[2] or '')[:27]:<28} "
              f"{r[3]:<7} {amt:>10.2f} {r[6]:>12.2f}")

    print(f"\n  Showing {len(rows)} rows.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = sys.argv[1:]
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    if not args:
        print(__doc__)
        conn.close()
        return

    if args[0] == "--sync-accounts":
        n = sync_accounts(conn)
        print(f"  Synced {n} accounts.")
        conn.close()
        return

    if args[0] == "--import-csv":
        if len(args) < 2:
            print("[error] Provide CSV path: python sync_wave.py --import-csv transactions.csv")
            sys.exit(1)
        import_csv(conn, args[1])
        conn.close()
        return

    if args[0] == "--status":
        print_status(conn)
        conn.close()
        return

    if args[0] == "--list":
        prefix = args[1] if len(args) > 1 else ""
        limit  = int(args[2]) if len(args) > 2 else 30
        print_list(conn, prefix, limit)
        conn.close()
        return

    print(__doc__)
    conn.close()


if __name__ == "__main__":
    main()
