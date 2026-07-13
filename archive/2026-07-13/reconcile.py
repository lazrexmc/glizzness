#!/usr/bin/env python3
"""
Glizzness Square → Wave Reconciliation
Pulls Square payouts/payments/orders and creates GAAP-compliant
journal entries in Wave Accounting. Tracks state in SQLite.

Usage:
  python reconcile.py                        # process yesterday
  python reconcile.py 2025-01-01 2025-12-31  # backfill a range
  python reconcile.py 2025-06-09             # single day
"""

import os
import sys
import json
import sqlite3
import time
import requests
from datetime import date, datetime, timedelta, timezone

# ── Configuration ───────────────────────────────────────────────────────────
SQUARE_TOKEN     = os.environ.get("SQUARE_TOKEN", "")
WAVE_TOKEN       = os.environ.get("WAVE_TOKEN", "")
WAVE_BUSINESS_ID = os.environ.get("WAVE_BUSINESS_ID", "")

# Wave Chart of Accounts IDs — populate via: python reconcile.py --list-accounts
WAVE_ACCOUNTS = {
    "bank":              os.environ.get("WAVE_BANK_ACCOUNT_ID", ""),
    "sales_revenue":     os.environ.get("WAVE_SALES_REVENUE_ID", ""),
    "tips_income":       os.environ.get("WAVE_TIPS_INCOME_ID", ""),
    "processing_fees":   os.environ.get("WAVE_PROCESSING_FEES_ID", ""),
    "sales_tax_payable": os.environ.get("WAVE_SALES_TAX_ID", ""),
    "sales_returns":     os.environ.get("WAVE_SALES_RETURNS_ID", ""),
    "discounts_comps":   os.environ.get("WAVE_DISCOUNTS_ID", ""),
}

SQUARE_BASE    = "https://connect.squareup.com/v2"
WAVE_GQL       = "https://gql.waveapps.com/graphql/public"
DB_PATH        = "glizzness_reconciliation.db"
VARIANCE_LIMIT = 10  # cents — warn if calc net vs payout net differs by more than $0.10

SQUARE_HEADERS = {
    "Authorization": f"Bearer {SQUARE_TOKEN}",
    "Square-Version": "2025-01-23",
    "Content-Type": "application/json",
}
WAVE_HEADERS = {
    "Authorization": f"Bearer {WAVE_TOKEN}",
    "Content-Type": "application/json",
}


# ── Database ────────────────────────────────────────────────────────────────
def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS payouts (
        payout_id     TEXT PRIMARY KEY,
        arrival_date  TEXT NOT NULL,
        created_at    TEXT,
        amount_cents  INTEGER NOT NULL,
        status        TEXT,
        location_id   TEXT,
        processed     INTEGER DEFAULT 0,
        wave_entry_id TEXT,
        processed_at  TEXT
    );

    CREATE TABLE IF NOT EXISTS payments (
        payment_id        TEXT PRIMARY KEY,
        payout_id         TEXT,
        order_id          TEXT,
        created_at        TEXT,
        delayed_until     TEXT,
        amount_cents      INTEGER,
        tip_cents         INTEGER DEFAULT 0,
        total_cents       INTEGER,
        fee_cents         INTEGER DEFAULT 0,
        tax_cents         INTEGER DEFAULT 0,
        discount_cents    INTEGER DEFAULT 0,
        gross_sales_cents INTEGER,
        square_product    TEXT,
        status            TEXT,
        FOREIGN KEY (payout_id) REFERENCES payouts(payout_id)
    );

    CREATE TABLE IF NOT EXISTS run_log (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        run_at            TEXT,
        date_range        TEXT,
        payouts_found     INTEGER DEFAULT 0,
        entries_created   INTEGER DEFAULT 0,
        skipped           INTEGER DEFAULT 0,
        errors            TEXT
    );
    """)
    conn.commit()


# ── Square API helpers ──────────────────────────────────────────────────────
def sq_get(path: str, params: dict = None) -> dict:
    resp = requests.get(
        f"{SQUARE_BASE}{path}",
        headers=SQUARE_HEADERS,
        params=params or {},
    )
    resp.raise_for_status()
    return resp.json()


def get_payouts(begin_date: str, end_date: str) -> list:
    """
    Return PAID payouts whose arrival_date falls within begin_date..end_date.

    Square's begin_time/end_time filters by created_at, not arrival_date.
    A payout arriving on Oct 22 was created ~2 days earlier, so we fetch a
    wider window (begin_date - 7 days) and filter by arrival_date in Python.
    """
    fetch_begin = (
        datetime.strptime(begin_date, "%Y-%m-%d").date() - timedelta(days=7)
    ).strftime("%Y-%m-%d")

    payouts, cursor = [], None
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
            if p.get("status") != "PAID":
                continue
            arrival = p.get("arrival_date", "")
            if begin_date <= arrival <= end_date:
                payouts.append(p)
        cursor = data.get("cursor")
        if not cursor:
            break
        time.sleep(0.1)
    return payouts


def get_payments_for_arrival(arrival_date: str) -> list:
    """
    Return COMPLETED payments whose delayed_until date matches arrival_date.
    Searches an 8-day window before arrival to cover both POS (PT36H)
    and invoice (PT168H / 7-day) payment types.
    """
    arrival  = datetime.strptime(arrival_date, "%Y-%m-%d").date()
    begin    = (arrival - timedelta(days=8)).strftime("%Y-%m-%d")
    matched, cursor = [], None

    while True:
        params = {
            "begin_time": f"{begin}T00:00:00-06:00",
            "end_time":   f"{arrival_date}T23:59:59-06:00",
            "limit":      100,
        }
        if cursor:
            params["cursor"] = cursor
        data = sq_get("/payments", params)
        for p in data.get("payments", []):
            if p.get("status") != "COMPLETED":
                continue
            delayed = p.get("delayed_until", "")
            if delayed and delayed[:10] == arrival_date:
                matched.append(p)
        cursor = data.get("cursor")
        if not cursor:
            break
        time.sleep(0.1)
    return matched


def get_order(order_id: str) -> dict:
    """Fetch a single order; return empty dict on failure."""
    try:
        return sq_get(f"/orders/{order_id}").get("order", {})
    except Exception as e:
        print(f"    [warn] order {order_id} fetch failed: {e}")
        return {}


def enrich_with_order(payment: dict) -> dict:
    """Attach tax_cents, discount_cents, gross_sales_cents from the order."""
    order_id = payment.get("order_id")
    if not order_id:
        payment["tax_cents"]          = 0
        payment["discount_cents"]     = 0
        payment["gross_sales_cents"]  = payment.get("amount_money", {}).get("amount", 0)
        return payment

    order = get_order(order_id)
    time.sleep(0.05)

    payment["tax_cents"]      = order.get("total_tax_money", {}).get("amount", 0)
    payment["discount_cents"] = order.get("total_discount_money", {}).get("amount", 0)

    # Gross sales = sum of line item gross_sales_money (pre-discount)
    gross = sum(
        item.get("gross_sales_money", {}).get("amount", 0)
        for item in order.get("line_items", [])
    )
    payment["gross_sales_cents"] = gross or payment.get("amount_money", {}).get("amount", 0)
    return payment


def aggregate_payments(payments: list) -> dict:
    """Sum all accounting fields across a list of enriched payments."""
    return {
        "gross_sales": sum(p.get("gross_sales_cents", 0) for p in payments),
        "tips":        sum(p.get("tip_money", {}).get("amount", 0) for p in payments),
        "taxes":       sum(p.get("tax_cents", 0) for p in payments),
        "discounts":   sum(p.get("discount_cents", 0) for p in payments),
        "fees":        sum(
                           sum(f.get("amount_money", {}).get("amount", 0)
                               for f in p.get("processing_fee", []))
                           for p in payments
                       ),
        "returns":     0,  # refund handling below
    }


# ── Wave API ────────────────────────────────────────────────────────────────
CREATE_TRANSACTION = """
mutation CreateTransaction($input: MoneyTransactionCreateInput!) {
    moneyTransactionCreate(input: $input) {
        didSucceed
        inputErrors { message path code }
        transaction { id description }
    }
}
"""

LIST_BUSINESSES = """
query ListBusinesses {
    businesses(page: 1, pageSize: 20) {
        edges {
            node { id name }
        }
    }
}
"""

LIST_ACCOUNTS = """
query ListAccounts($businessId: ID!) {
    business(id: $businessId) {
        accounts(page: 1, pageSize: 100) {
            edges {
                node { id name type { name } subtype { name } }
            }
        }
    }
}
"""


def wave_query(query: str, variables: dict) -> dict:
    resp = requests.post(
        WAVE_GQL,
        headers=WAVE_HEADERS,
        json={"query": query, "variables": variables},
    )
    resp.raise_for_status()
    return resp.json()


def list_wave_accounts() -> None:
    """Print all Wave accounts so you can populate WAVE_ACCOUNTS env vars."""
    result = wave_query(LIST_ACCOUNTS, {"businessId": WAVE_BUSINESS_ID})

    # Surface any GraphQL errors before trying to parse
    if result.get("errors"):
        print(f"\n[error] Wave API errors:")
        for e in result["errors"]:
            print(f"  {e.get('message', e)}")
        return

    business = (result.get("data") or {}).get("business")
    if not business:
        print(f"\n[error] No business returned. Raw response:")
        print(json.dumps(result, indent=2))
        print(f"\nCurrent WAVE_BUSINESS_ID = '{WAVE_BUSINESS_ID}'")
        print("Run the query below to find your correct business ID:")
        print("\n  python reconcile.py --list-businesses\n")
        return

    edges = business.get("accounts", {}).get("edges", [])
    print(f"\n{'ID':<30} {'Type':<20} {'Subtype':<25} Name")
    print("-" * 100)
    for e in edges:
        n = e["node"]
        print(f"{n['id']:<30} {n['type']['name']:<20} {n['subtype']['name']:<25} {n['name']}")


def create_journal_entry(
    arrival_date: str,
    payout_id: str,
    gross_sales: int,
    tips: int,
    taxes: int,
    discounts: int,
    returns: int,
    fees: int,
    net: int,
) -> dict:
    """Post a GAAP-compliant multi-line journal entry to Wave. Amounts in cents."""

    def d(cents: int) -> str:
        return f"{abs(cents) / 100:.2f}"

    lines = [
        {
            "accountId":   WAVE_ACCOUNTS["bank"],
            "amount":      d(net),
            "balance":     "DEBIT",
            "description": "Square net deposit",
        },
        {
            "accountId":   WAVE_ACCOUNTS["processing_fees"],
            "amount":      d(fees),
            "balance":     "DEBIT",
            "description": "Square processing fees",
        },
        {
            "accountId":   WAVE_ACCOUNTS["sales_revenue"],
            "amount":      d(gross_sales),
            "balance":     "CREDIT",
            "description": "Gross sales",
        },
    ]

    if tips > 0:
        lines.append({
            "accountId":   WAVE_ACCOUNTS["tips_income"],
            "amount":      d(tips),
            "balance":     "CREDIT",
            "description": "Tips — owner",
        })

    if taxes > 0:
        lines.append({
            "accountId":   WAVE_ACCOUNTS["sales_tax_payable"],
            "amount":      d(taxes),
            "balance":     "CREDIT",
            "description": "Sales tax collected",
        })

    if discounts > 0:
        lines.append({
            "accountId":   WAVE_ACCOUNTS["discounts_comps"],
            "amount":      d(discounts),
            "balance":     "DEBIT",
            "description": "Discounts & comps",
        })

    if returns > 0:
        lines.append({
            "accountId":   WAVE_ACCOUNTS["sales_returns"],
            "amount":      d(returns),
            "balance":     "DEBIT",
            "description": "Returns & refunds",
        })

    return wave_query(CREATE_TRANSACTION, {
        "input": {
            "businessId": WAVE_BUSINESS_ID,
            "externalId": payout_id,
            "date":        arrival_date,
            "description": f"Square Settlement {arrival_date}",
            "lineItems":   lines,
        }
    })


# ── Core reconciliation ─────────────────────────────────────────────────────
def process_payout(conn: sqlite3.Connection, payout: dict) -> str:
    """
    Process a single payout. Returns 'created', 'skipped', or 'error'.
    """
    payout_id    = payout["id"]
    arrival_date = payout["arrival_date"]
    payout_net   = payout["amount_money"]["amount"]

    # Skip if already processed
    row = conn.execute(
        "SELECT processed FROM payouts WHERE payout_id = ?", (payout_id,)
    ).fetchone()
    if row and row[0]:
        print(f"  [skip] {payout_id[:16]}  {arrival_date}  already posted")
        return "skipped"

    print(f"\n  Payout {payout_id[:16]}  {arrival_date}  ${payout_net/100:.2f}")

    # Upsert payout record
    conn.execute("""
        INSERT OR IGNORE INTO payouts
            (payout_id, arrival_date, created_at, amount_cents, status, location_id)
        VALUES (?,?,?,?,?,?)
    """, (payout_id, arrival_date, payout.get("created_at"),
          payout_net, payout.get("status"), payout.get("location_id")))
    conn.commit()

    # Fetch payments linked to this payout via delayed_until date
    raw = get_payments_for_arrival(arrival_date)
    print(f"    {len(raw)} payment(s) found — fetching orders...")

    if not raw:
        print(f"    [warn] no payments found — skipping entry creation")
        return "error"

    payments = [enrich_with_order(p) for p in raw]
    sums     = aggregate_payments(payments)

    calc_net = (sums["gross_sales"] + sums["tips"] + sums["taxes"]
                - sums["discounts"] - sums["returns"] - sums["fees"])

    variance = abs(calc_net - payout_net)
    print(f"    Gross ${sums['gross_sales']/100:.2f} | "
          f"Tips ${sums['tips']/100:.2f} | "
          f"Tax ${sums['taxes']/100:.2f} | "
          f"Disc ${sums['discounts']/100:.2f} | "
          f"Fees ${sums['fees']/100:.2f}")
    print(f"    Calc net ${calc_net/100:.2f}  |  "
          f"Payout net ${payout_net/100:.2f}  |  "
          f"Variance ${variance/100:.2f}")

    if variance > VARIANCE_LIMIT:
        print(f"    [warn] variance ${variance/100:.2f} exceeds threshold — "
              f"review manually before posting")

    # Persist payments
    for p in payments:
        fee = sum(f.get("amount_money", {}).get("amount", 0)
                  for f in p.get("processing_fee", []))
        conn.execute("""
            INSERT OR IGNORE INTO payments
                (payment_id, payout_id, order_id, created_at, delayed_until,
                 amount_cents, tip_cents, total_cents, fee_cents,
                 tax_cents, discount_cents, gross_sales_cents,
                 square_product, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            p["id"], payout_id, p.get("order_id"),
            p.get("created_at"), p.get("delayed_until"),
            p.get("amount_money", {}).get("amount", 0),
            p.get("tip_money", {}).get("amount", 0),
            p.get("total_money", {}).get("amount", 0),
            fee,
            p.get("tax_cents", 0),
            p.get("discount_cents", 0),
            p.get("gross_sales_cents", 0),
            p.get("application_details", {}).get("square_product", ""),
            p.get("status"),
        ))
    conn.commit()

    # Create Wave journal entry
    result    = create_journal_entry(
        arrival_date=arrival_date,
        payout_id=payout_id,
        gross_sales=sums["gross_sales"],
        tips=sums["tips"],
        taxes=sums["taxes"],
        discounts=sums["discounts"],
        returns=sums["returns"],
        fees=sums["fees"],
        net=payout_net,
    )
    gql = result.get("data", {}).get("moneyTransactionCreate", {})

    if gql.get("didSucceed"):
        wave_id = gql.get("transaction", {}).get("id", "")
        print(f"    [ok] Wave entry created — {wave_id}")
        conn.execute("""
            UPDATE payouts
            SET processed = 1, wave_entry_id = ?, processed_at = ?
            WHERE payout_id = ?
        """, (wave_id, datetime.now(timezone.utc).isoformat(), payout_id))
        conn.commit()
        return "created"
    else:
        errs = gql.get("inputErrors", [])
        print(f"    [error] Wave entry failed: {errs}")
        return "error"


# ── Entry point ─────────────────────────────────────────────────────────────
def main() -> None:
    args = sys.argv[1:]

    # Business listing helper — run first if you don't know your business ID
    if args and args[0] == "--list-businesses":
        if not WAVE_TOKEN:
            print("Set WAVE_TOKEN env var first.")
            sys.exit(1)
        result = wave_query(LIST_BUSINESSES, {})
        if result.get("errors"):
            print("[error]", result["errors"])
            sys.exit(1)
        edges = (result.get("data") or {}).get("businesses", {}).get("edges", [])
        print(f"\n{'ID':<40} Name")
        print("-" * 70)
        for e in edges:
            n = e["node"]
            print(f"{n['id']:<40} {n['name']}")
        print("\nSet WAVE_BUSINESS_ID to the ID above, then run --list-accounts\n")
        return

    # Account listing helper — run once to find Wave account IDs
    if args and args[0] == "--list-accounts":
        if not WAVE_TOKEN or not WAVE_BUSINESS_ID:
            print("Set WAVE_TOKEN and WAVE_BUSINESS_ID env vars first.")
            sys.exit(1)
        list_wave_accounts()
        return

    # Date range
    if len(args) == 2:
        begin_date, end_date = args[0], args[1]
    elif len(args) == 1:
        begin_date = end_date = args[0]
    else:
        yesterday  = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        begin_date = end_date = yesterday

    print(f"\n{'='*62}")
    print(f"  Glizzness Square → Wave Reconciliation")
    print(f"  Range: {begin_date}  →  {end_date}")
    print(f"{'='*62}")

    if not all([SQUARE_TOKEN, WAVE_TOKEN, WAVE_BUSINESS_ID]):
        print("\n[error] Missing env vars. Set SQUARE_TOKEN, WAVE_TOKEN, WAVE_BUSINESS_ID.")
        sys.exit(1)

    missing = [k for k, v in WAVE_ACCOUNTS.items() if not v]
    if missing:
        print(f"\n[warn] Missing Wave account IDs: {missing}")
        print("  Run: python reconcile.py --list-accounts")
        print("  Then set the corresponding env vars.\n")

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    payouts = get_payouts(begin_date, end_date)
    print(f"\n  {len(payouts)} PAID payout(s) found")

    counts = {"created": 0, "skipped": 0, "error": 0}
    errors = []

    for payout in payouts:
        result = process_payout(conn, payout)
        counts[result] += 1
        if result == "error":
            errors.append(payout["id"])

    conn.execute("""
        INSERT INTO run_log (run_at, date_range, payouts_found, entries_created, skipped, errors)
        VALUES (?,?,?,?,?,?)
    """, (datetime.now(timezone.utc).isoformat(), f"{begin_date}/{end_date}",
          len(payouts), counts["created"], counts["skipped"], json.dumps(errors)))
    conn.commit()
    conn.close()

    print(f"\n{'='*62}")
    print(f"  Created: {counts['created']}  |  "
          f"Skipped: {counts['skipped']}  |  "
          f"Errors: {counts['error']}")
    if errors:
        print(f"  Failed payout IDs: {errors}")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
