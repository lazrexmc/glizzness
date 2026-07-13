#!/usr/bin/env python3
"""
sync_square.py — Download all Square data into a local SQLite database.

Usage:
  python sync_square.py                        # sync current year to today
  python sync_square.py 2025-01-01 2025-12-31  # explicit range
  python sync_square.py --status               # print row counts and payout summary
  python sync_square.py --show-payout po_12c2861b  # detail one payout
"""

import os
import sys
import json
import re
import sqlite3
import time
import requests
from datetime import date, datetime, timedelta, timezone

SQUARE_TOKEN  = os.environ.get("SQUARE_TOKEN", "")
SQUARE_BASE   = "https://connect.squareup.com/v2"
SQUARE_HEADERS = {
    "Authorization": f"Bearer {SQUARE_TOKEN}",
    "Square-Version": "2025-01-23",
    "Content-Type": "application/json",
}

DB_PATH = "glizzness.db"


# ── Database ────────────────────────────────────────────────────────────────
def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS payouts (
        payout_id       TEXT PRIMARY KEY,
        status          TEXT,
        arrival_date    TEXT,
        created_at      TEXT,
        updated_at      TEXT,
        amount_cents    INTEGER,
        currency        TEXT,
        location_id     TEXT,
        destination_id  TEXT,
        raw_json        TEXT
    );

    -- Each line item inside a payout (one row per payment/refund in the deposit)
    CREATE TABLE IF NOT EXISTS payout_entries (
        entry_id            TEXT PRIMARY KEY,
        payout_id           TEXT NOT NULL,
        effective_at        TEXT,
        type                TEXT,          -- CHARGE, REFUND, FEE, etc.
        gross_cents         INTEGER,
        fee_cents           INTEGER,
        net_cents           INTEGER,
        payment_id          TEXT,          -- populated for CHARGE / REFUND entries
        raw_json            TEXT,
        FOREIGN KEY (payout_id) REFERENCES payouts(payout_id)
    );

    CREATE TABLE IF NOT EXISTS payments (
        payment_id          TEXT PRIMARY KEY,
        order_id            TEXT,
        created_at          TEXT,
        updated_at          TEXT,
        status              TEXT,
        source_type         TEXT,
        delay_duration      TEXT,
        amount_cents        INTEGER,
        tip_cents           INTEGER,
        total_cents         INTEGER,
        fee_cents           INTEGER,
        square_product      TEXT,
        location_id         TEXT,
        raw_json            TEXT
    );

    CREATE TABLE IF NOT EXISTS orders (
        order_id                   TEXT PRIMARY KEY,
        state                      TEXT,
        created_at                 TEXT,
        updated_at                 TEXT,
        location_id                TEXT,
        total_money_cents          INTEGER,
        total_tax_cents            INTEGER,
        total_discount_cents       INTEGER,
        total_tip_cents            INTEGER,
        total_service_charge_cents INTEGER,
        net_total_cents            INTEGER,
        raw_json                   TEXT
    );

    CREATE TABLE IF NOT EXISTS sync_log (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        synced_at        TEXT,
        date_range       TEXT,
        payouts_found    INTEGER DEFAULT 0,
        entries_found    INTEGER DEFAULT 0,
        payments_found   INTEGER DEFAULT 0,
        orders_found     INTEGER DEFAULT 0,
        errors           TEXT
    );
    """)
    # Migrate existing sync_log tables that predate entries_found column
    cols = [r[1] for r in conn.execute("PRAGMA table_info(sync_log)").fetchall()]
    if "entries_found" not in cols:
        conn.execute("ALTER TABLE sync_log ADD COLUMN entries_found INTEGER DEFAULT 0")
    conn.commit()


# ── Square API ───────────────────────────────────────────────────────────────
def sq_get(path: str, params: dict = None) -> dict:
    if not SQUARE_TOKEN:
        print("[error] SQUARE_TOKEN env var not set.")
        sys.exit(1)
    resp = requests.get(
        f"{SQUARE_BASE}{path}",
        headers=SQUARE_HEADERS,
        params=params or {},
    )
    if not resp.ok:
        print(f"  [http {resp.status_code}] {path} → {resp.text[:300]}")
        resp.raise_for_status()
    return resp.json()


# ── Fetch payouts ────────────────────────────────────────────────────────────
def fetch_payouts(begin_date: str, end_date: str) -> list:
    """
    Square's begin_time/end_time filters by created_at, not arrival_date.
    Fetch a 7-day-wider window and filter by arrival_date in Python.
    """
    fetch_begin = (
        datetime.strptime(begin_date, "%Y-%m-%d").date() - timedelta(days=7)
    ).strftime("%Y-%m-%d")

    result, cursor = [], None
    print(f"  Fetching payouts (arrival {begin_date} – {end_date})...")
    while True:
        params = {
            "begin_time": f"{fetch_begin}T00:00:00Z",
            "end_time":   f"{end_date}T23:59:59Z",
            "sort_order": "ASC",
            "limit":      100,
        }
        if cursor:
            params["cursor"] = cursor
        data = sq_get("/payouts", params)
        for p in data.get("payouts", []):
            if p.get("status") not in ("PAID", "SENT"):
                continue
            if begin_date <= p.get("arrival_date", "") <= end_date:
                result.append(p)
        cursor = data.get("cursor")
        if not cursor:
            break
        time.sleep(0.1)
    print(f"  → {len(result)} PAID payout(s)")
    return result


# ── Fetch payout entries (the definitive payment → payout link) ─────────────
def fetch_payout_entries(payout_id: str) -> list:
    """
    Returns every line item in a payout: charges, refunds, fees, adjustments.
    This is the authoritative link between a payout and its payments.
    """
    entries, cursor = [], None
    while True:
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        data = sq_get(f"/payouts/{payout_id}/payout-entries", params)
        entries.extend(data.get("payout_entries", []))
        cursor = data.get("cursor")
        if not cursor:
            break
        time.sleep(0.05)
    return entries


# ── Fetch payments ───────────────────────────────────────────────────────────
def fetch_payments(begin_date: str, end_date: str) -> list:
    result, cursor = [], None
    print(f"  Fetching payments ({begin_date} – {end_date})...")
    while True:
        params = {
            "begin_time": f"{begin_date}T00:00:00Z",
            "end_time":   f"{end_date}T23:59:59Z",
            "limit":      100,
        }
        if cursor:
            params["cursor"] = cursor
        data = sq_get("/payments", params)
        for p in data.get("payments", []):
            if p.get("status") == "COMPLETED":
                result.append(p)
        cursor = data.get("cursor")
        if not cursor:
            break
        time.sleep(0.1)
    print(f"  → {len(result)} COMPLETED payment(s)")
    return result


# ── Fetch a single order ─────────────────────────────────────────────────────
def fetch_order(order_id: str) -> dict:
    try:
        return sq_get(f"/orders/{order_id}").get("order", {})
    except Exception as e:
        print(f"    [warn] order {order_id}: {e}")
        return {}


# ── Upsert helpers ───────────────────────────────────────────────────────────
def upsert_payout(conn: sqlite3.Connection, p: dict) -> None:
    conn.execute("""
        INSERT OR REPLACE INTO payouts
            (payout_id, status, arrival_date, created_at, updated_at,
             amount_cents, currency, location_id, destination_id, raw_json)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        p["id"], p.get("status"), p.get("arrival_date"),
        p.get("created_at"), p.get("updated_at"),
        p.get("amount_money", {}).get("amount", 0),
        p.get("amount_money", {}).get("currency", "USD"),
        p.get("location_id"),
        p.get("destination", {}).get("id"),
        json.dumps(p),
    ))


def upsert_entry(conn: sqlite3.Connection, e: dict) -> None:
    details = e.get("type_charge_details") or e.get("type_refund_details") or {}
    conn.execute("""
        INSERT OR REPLACE INTO payout_entries
            (entry_id, payout_id, effective_at, type,
             gross_cents, fee_cents, net_cents, payment_id, raw_json)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        e["id"], e["payout_id"], e.get("effective_at"), e.get("type"),
        e.get("gross_amount_money", {}).get("amount", 0),
        e.get("fee_amount_money", {}).get("amount", 0),
        e.get("net_amount_money", {}).get("amount", 0),
        details.get("payment_id"),
        json.dumps(e),
    ))


def upsert_payment(conn: sqlite3.Connection, p: dict) -> None:
    fee = sum(
        f.get("amount_money", {}).get("amount", 0)
        for f in p.get("processing_fee", [])
    )
    conn.execute("""
        INSERT OR REPLACE INTO payments
            (payment_id, order_id, created_at, updated_at, status,
             source_type, delay_duration,
             amount_cents, tip_cents, total_cents, fee_cents,
             square_product, location_id, raw_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        p["id"], p.get("order_id"),
        p.get("created_at"), p.get("updated_at"), p.get("status"),
        p.get("source_type"), p.get("delay_duration"),
        p.get("amount_money", {}).get("amount", 0),
        p.get("tip_money", {}).get("amount", 0),
        p.get("total_money", {}).get("amount", 0),
        fee,
        p.get("application_details", {}).get("square_product", ""),
        p.get("location_id"),
        json.dumps(p),
    ))


def upsert_order(conn: sqlite3.Connection, o: dict) -> None:
    conn.execute("""
        INSERT OR REPLACE INTO orders
            (order_id, state, created_at, updated_at, location_id,
             total_money_cents, total_tax_cents, total_discount_cents,
             total_tip_cents, total_service_charge_cents,
             net_total_cents, raw_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        o["id"], o.get("state"),
        o.get("created_at"), o.get("updated_at"), o.get("location_id"),
        o.get("total_money", {}).get("amount", 0),
        o.get("total_tax_money", {}).get("amount", 0),
        o.get("total_discount_money", {}).get("amount", 0),
        o.get("total_tip_money", {}).get("amount", 0),
        o.get("total_service_charge_money", {}).get("amount", 0),
        o.get("net_amounts", {}).get("total_money", {}).get("amount", 0),
        json.dumps(o),
    ))


# ── Status report ────────────────────────────────────────────────────────────
def print_status(conn: sqlite3.Connection) -> None:
    for table in ["payouts", "payout_entries", "payments", "orders", "sync_log"]:
        try:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            print(f"  {table:<20} {row[0]:>6} rows")
        except Exception:
            print(f"  {table:<20}  (table not found — re-run sync)")

    print()
    rows = conn.execute("""
        SELECT arrival_date, COUNT(*) as n, SUM(amount_cents) as total
        FROM payouts GROUP BY arrival_date
        ORDER BY arrival_date DESC LIMIT 20
    """).fetchall()
    if rows:
        print(f"  {'Arrival Date':<15} {'Payouts':>8} {'Total':>12}")
        print("  " + "-" * 38)
        for r in rows:
            print(f"  {r[0]:<15} {r[1]:>8} ${r[2]/100:>11.2f}")


# ── Show payout detail ───────────────────────────────────────────────────────
def print_payout(conn: sqlite3.Connection, payout_id: str) -> None:
    p = conn.execute(
        "SELECT * FROM payouts WHERE payout_id LIKE ?", (f"{payout_id}%",)
    ).fetchone()
    if not p:
        print(f"  No payout found matching '{payout_id}'")
        return

    cols = [d[0] for d in conn.execute("SELECT * FROM payouts LIMIT 0").description]
    payout = dict(zip(cols, p))
    print(f"\nPayout: {payout['payout_id']}")
    print(f"  Arrival:  {payout['arrival_date']}")
    print(f"  Amount:   ${payout['amount_cents']/100:.2f}")
    print(f"  Status:   {payout['status']}")

    entries = conn.execute("""
        SELECT pe.entry_id, pe.effective_at, pe.type,
               pe.gross_cents, pe.fee_cents, pe.net_cents, pe.payment_id,
               pm.amount_cents, pm.tip_cents, pm.square_product, pm.order_id,
               o.total_tax_cents, o.total_discount_cents
        FROM payout_entries pe
        LEFT JOIN payments pm ON pe.payment_id = pm.payment_id
        LEFT JOIN orders o ON pm.order_id = o.order_id
        WHERE pe.payout_id = ?
        ORDER BY pe.effective_at
    """, (payout['payout_id'],)).fetchall()

    if not entries:
        print("\n  No payout entries in database — run sync to fetch them.")
        return

    gross = tips = fees = taxes = discounts = net_total = 0
    print(f"\n  {'Type':<8} {'Effective':<22} {'Sale':>8} {'Tip':>7} "
          f"{'Fee':>7} {'Tax':>6} {'Disc':>6} {'Net':>9}  Product")
    print("  " + "-" * 105)

    for e in entries:
        (entry_id, eff_at, etype, e_gross, e_fee, e_net, pay_id,
         sale, tip, product, order_id, tax, disc) = e
        sale = sale or 0
        tip  = tip  or 0
        tax  = tax  or 0
        disc = disc or 0
        print(f"  {etype:<8} {(eff_at or '')[:19]:<22} "
              f"${sale/100:>7.2f} ${tip/100:>6.2f} "
              f"${e_fee/100:>6.2f} ${tax/100:>5.2f} ${disc/100:>5.2f} "
              f"${e_net/100:>8.2f}  {product or ''}")
        gross     += e_gross
        fees      += e_fee
        tips      += tip
        taxes     += tax
        discounts += disc
        net_total += e_net

    print("  " + "-" * 105)
    print(f"  {'TOTALS':<8} {'':22} ${(gross-tips)/100:>7.2f} ${tips/100:>6.2f} "
          f"${fees/100:>6.2f} ${taxes/100:>5.2f} ${discounts/100:>5.2f} "
          f"${net_total/100:>8.2f}")
    print(f"\n  Payout net: ${payout['amount_cents']/100:.2f}  |  "
          f"Entries net: ${net_total/100:.2f}  |  "
          f"Variance: ${abs(net_total - payout['amount_cents'])/100:.2f}")


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    args = sys.argv[1:]

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    if args and args[0] == "--status":
        print(f"\nDatabase: {DB_PATH}")
        print_status(conn)
        conn.close()
        return

    if args and args[0] == "--show-payout":
        pid = args[1] if len(args) > 1 else ""
        if not pid:
            print("Usage: python sync_square.py --show-payout <payout_id_prefix>")
            sys.exit(1)
        print_payout(conn, pid)
        conn.close()
        return

    # Date range
    if len(args) == 2 and not args[0].startswith("--"):
        begin_date, end_date = args[0], args[1]
    elif len(args) == 1 and not args[0].startswith("--"):
        begin_date = end_date = args[0]
    else:
        begin_date = f"{date.today().year}-01-01"
        end_date   = date.today().strftime("%Y-%m-%d")

    if not SQUARE_TOKEN:
        print("[error] Set SQUARE_TOKEN env var first.")
        sys.exit(1)

    print(f"\n{'='*62}")
    print(f"  Square Data Sync  →  {DB_PATH}")
    print(f"  Range: {begin_date}  →  {end_date}")
    print(f"{'='*62}\n")

    # ── 1. Payouts ───────────────────────────────────────────────────────────
    payouts = fetch_payouts(begin_date, end_date)
    for p in payouts:
        upsert_payout(conn, p)
    conn.commit()

    # ── 2. Payout entries (payment → payout definitive link) ─────────────────
    # Only fetch entries for payouts not yet in the entries table
    need_entries = conn.execute("""
        SELECT p.payout_id FROM payouts p
        WHERE NOT EXISTS (
            SELECT 1 FROM payout_entries e WHERE e.payout_id = p.payout_id
        )
    """).fetchall()
    need_entries = [r[0] for r in need_entries]

    print(f"  Fetching payout entries for {len(need_entries)} payout(s)...")
    total_entries = 0
    for i, pid in enumerate(need_entries, 1):
        entries = fetch_payout_entries(pid)
        for e in entries:
            upsert_entry(conn, e)
        total_entries += len(entries)
        if i % 10 == 0:
            conn.commit()
            print(f"    {i}/{len(need_entries)}...")
    conn.commit()
    print(f"  → {total_entries} payout entr{'y' if total_entries == 1 else 'ies'}")

    # ── 3. Payments ──────────────────────────────────────────────────────────
    # Collect all payment IDs referenced in payout entries but not yet fetched
    missing_payment_ids = conn.execute("""
        SELECT DISTINCT pe.payment_id
        FROM payout_entries pe
        LEFT JOIN payments pm ON pe.payment_id = pm.payment_id
        WHERE pe.payment_id IS NOT NULL AND pm.payment_id IS NULL
    """).fetchall()
    missing_payment_ids = [r[0] for r in missing_payment_ids]

    if missing_payment_ids:
        print(f"  Fetching {len(missing_payment_ids)} missing payment(s) by ID...")
        # Also do a date-range pull to catch everything (more efficient than per-ID)
        pay_begin = (
            datetime.strptime(begin_date, "%Y-%m-%d").date() - timedelta(days=8)
        ).strftime("%Y-%m-%d")
        payments = fetch_payments(pay_begin, end_date)
        for p in payments:
            upsert_payment(conn, p)
        conn.commit()
    else:
        # Still do a date-range pull to keep payments table complete
        pay_begin = (
            datetime.strptime(begin_date, "%Y-%m-%d").date() - timedelta(days=8)
        ).strftime("%Y-%m-%d")
        payments = fetch_payments(pay_begin, end_date)
        for p in payments:
            upsert_payment(conn, p)
        conn.commit()

    # ── 4. Orders ────────────────────────────────────────────────────────────
    order_ids = conn.execute("""
        SELECT DISTINCT p.order_id
        FROM payments p
        LEFT JOIN orders o ON p.order_id = o.order_id
        WHERE p.order_id IS NOT NULL AND o.order_id IS NULL
    """).fetchall()
    order_ids = [r[0] for r in order_ids]

    print(f"  Fetching {len(order_ids)} new order(s)...")
    for i, oid in enumerate(order_ids, 1):
        order = fetch_order(oid)
        if order:
            upsert_order(conn, order)
        if i % 20 == 0:
            conn.commit()
            print(f"    {i}/{len(order_ids)}...")
        time.sleep(0.05)
    conn.commit()
    print(f"  → {len(order_ids)} order(s) fetched")

    # ── Log ──────────────────────────────────────────────────────────────────
    conn.execute("""
        INSERT INTO sync_log
            (synced_at, date_range, payouts_found, entries_found, payments_found, orders_found, errors)
        VALUES (?,?,?,?,?,?,?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        f"{begin_date}/{end_date}",
        len(payouts), total_entries, len(payments), len(order_ids),
        "[]",
    ))
    conn.commit()
    conn.close()

    print(f"\n{'='*62}")
    print(f"  Payouts: {len(payouts)}  |  Entries: {total_entries}  |  "
          f"Payments: {len(payments)}  |  Orders: {len(order_ids)}")
    print(f"  Saved to {DB_PATH}")
    print(f"\n  python sync_square.py --status")
    print(f"  python sync_square.py --show-payout po_12c2861b")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
