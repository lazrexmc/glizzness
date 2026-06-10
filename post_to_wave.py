#!/usr/bin/env python3
"""
post_to_wave.py — Stage, review, and post Wave journal entries.

Workflow:
  1. python post_to_wave.py --build                  # compute entries from Square DB
  2. python post_to_wave.py --review                 # inspect before touching Wave
  3. python post_to_wave.py --post                   # post staged entries to Wave

Other commands:
  python post_to_wave.py --build  2025-10-22         # build one day
  python post_to_wave.py --review 2025-10-22         # review one day
  python post_to_wave.py --status                    # counts by status
  python post_to_wave.py --introspect                # check Wave API schema
"""

import os
import sys
import json
import sqlite3
import requests
from datetime import date, datetime, timezone

WAVE_TOKEN       = os.environ.get("WAVE_TOKEN", "")
WAVE_BUSINESS_ID = os.environ.get("WAVE_BUSINESS_ID", "")

WAVE_ACCOUNTS = {
    "clearing":      os.environ.get("WAVE_CLEARING_ACCOUNT_ID", ""),
    "bank":          os.environ.get("WAVE_BANK_ACCOUNT_ID", ""),
    "sales_revenue": os.environ.get("WAVE_SALES_REVENUE_ID", ""),
    "tips":          os.environ.get("WAVE_TIPS_INCOME_ID", ""),
    "fees":          os.environ.get("WAVE_PROCESSING_FEES_ID", ""),
    "sales_tax":     os.environ.get("WAVE_SALES_TAX_ID", ""),
    "returns":       os.environ.get("WAVE_SALES_RETURNS_ID", ""),
    "discounts":     os.environ.get("WAVE_DISCOUNTS_ID", ""),
}

# Human-readable names for the review display
ACCOUNT_NAMES = {
    WAVE_ACCOUNTS.get("clearing"):      "Square Settlements Clearing",
    WAVE_ACCOUNTS.get("bank"):          "Checking (529)",
    WAVE_ACCOUNTS.get("sales_revenue"): "Food & Beverage Sales",
    WAVE_ACCOUNTS.get("tips"):          "Tips Collected",
    WAVE_ACCOUNTS.get("fees"):          "Merchant Account Fees",
    WAVE_ACCOUNTS.get("sales_tax"):     "Columbia Sales Tax",
    WAVE_ACCOUNTS.get("returns"):       "Sales Returns",
    WAVE_ACCOUNTS.get("discounts"):     "Customer Discounts",
}

WAVE_GQL = "https://gql.waveapps.com/graphql/public"
WAVE_HEADERS = {
    "Authorization": f"Bearer {WAVE_TOKEN}",
    "Content-Type": "application/json",
}

DB_PATH = "glizzness.db"


# ── Database ─────────────────────────────────────────────────────────────────
def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    -- One row per payout — the Wave journal entry to be created
    CREATE TABLE IF NOT EXISTS journal_entries (
        payout_id        TEXT PRIMARY KEY,
        arrival_date     TEXT NOT NULL,
        status           TEXT NOT NULL DEFAULT 'staged',
        -- status: staged | posted | error

        -- Aggregated amounts (cents)
        payout_net_cents   INTEGER,
        gross_sales_cents  INTEGER,
        tips_cents         INTEGER,
        taxes_cents        INTEGER,
        discounts_cents    INTEGER,
        returns_cents      INTEGER,
        fees_cents         INTEGER,

        -- Wave result
        wave_entry_id    TEXT,
        posted_at        TEXT,
        error_msg        TEXT,

        built_at         TEXT
    );

    -- Individual debit/credit lines for each journal entry
    CREATE TABLE IF NOT EXISTS journal_entry_lines (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        payout_id    TEXT NOT NULL,
        line_order   INTEGER,
        direction    TEXT,        -- DEBIT or CREDIT
        account_id   TEXT,
        account_name TEXT,
        amount_cents INTEGER,
        description  TEXT,
        FOREIGN KEY (payout_id) REFERENCES journal_entries(payout_id)
    );
    """)
    conn.commit()


# ── Wave API ─────────────────────────────────────────────────────────────────
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


INTROSPECT_ALL_TYPES = "query { __schema { types { name kind } } }"

QUERY_RECENT_TRANSACTIONS = """
query ($businessId: ID!, $page: Int!) {
  business(id: $businessId) {
    transactions(page: $page, pageSize: 10) {
      pageInfo { currentPage totalPages }
      edges {
        node {
          id
          description
          date
          amount
          account { id name }
          anchor { amount direction }
        }
      }
    }
  }
}
"""

INTROSPECT_INPUT_TYPE = """
query ($name: String!) {
  __type(name: $name) {
    name
    inputFields {
      name
      type {
        name kind
        ofType { name kind ofType { name kind ofType { name kind ofType { name kind } } } }
      }
    }
    enumValues { name }
  }
}
"""


def unwrap_type(t: dict) -> str:
    if not t:
        return "?"
    name = t.get("name")
    if name:
        return name
    kind = t.get("kind", "")
    inner = unwrap_type(t.get("ofType"))
    return f"[{inner}]" if kind == "LIST" else f"{inner}!" if kind == "NON_NULL" else inner


def introspect_type(type_name: str) -> None:
    result = wave_gql(INTROSPECT_INPUT_TYPE, {"name": type_name})
    itype = (result.get("data") or {}).get("__type")
    if not itype:
        print(f"  {type_name} — not found")
        return
    print(f"\n  {type_name}:")
    for f in itype.get("inputFields") or []:
        print(f"    {f['name']}: {unwrap_type(f['type'])}")
    for v in itype.get("enumValues") or []:
        print(f"    {v['name']}")


def introspect_wave() -> None:
    print("\nSearching for transaction-related input types...")
    all_result = wave_gql(INTROSPECT_ALL_TYPES, {})
    types = (all_result.get("data") or {}).get("__schema", {}).get("types", [])
    keywords = ("transaction", "lineitem", "lineitm", "split", "money")
    matches = [t["name"] for t in types
               if t["kind"] == "INPUT_OBJECT"
               and any(k in t["name"].lower() for k in keywords)]
    print(f"  Found: {matches}")
    for name in matches:
        introspect_type(name)
    introspect_type("TransactionDirection")


# ── Build entries from Square DB ─────────────────────────────────────────────
def build_entries(conn: sqlite3.Connection, begin_date: str, end_date: str) -> int:
    """
    Compute journal entries from Square data and save to journal_entries /
    journal_entry_lines tables. Overwrites any existing staged entries in range.
    Does NOT touch Wave.
    """
    payouts = conn.execute("""
        SELECT payout_id, arrival_date, amount_cents
        FROM payouts
        WHERE arrival_date BETWEEN ? AND ?
        ORDER BY arrival_date
    """, (begin_date, end_date)).fetchall()

    built = 0
    for payout_id, arrival_date, payout_net in payouts:

        # Skip if already posted to Wave
        existing = conn.execute(
            "SELECT status FROM journal_entries WHERE payout_id = ?", (payout_id,)
        ).fetchone()
        if existing and existing[0] == "posted":
            print(f"  [skip] {payout_id[:16]}  {arrival_date}  already posted")
            continue

        entries = conn.execute("""
            SELECT pe.type, pe.gross_cents, pe.fee_cents, pe.net_cents, pe.payment_id,
                   pm.amount_cents, pm.tip_cents,
                   o.total_tax_cents, o.total_discount_cents
            FROM payout_entries pe
            LEFT JOIN payments pm ON pe.payment_id = pm.payment_id
            LEFT JOIN orders o    ON pm.order_id   = o.order_id
            WHERE pe.payout_id = ?
        """, (payout_id,)).fetchall()

        if not entries:
            print(f"  [warn] {payout_id[:16]}  {arrival_date}  no entries — run sync first")
            continue

        gross_sales = tips = taxes = discounts = fees = returns = 0

        for (etype, e_gross, e_fee, e_net, pay_id,
             sale_cents, tip_cents, tax_cents, disc_cents) in entries:

            fees += e_fee or 0
            if etype == "CHARGE":
                sale = sale_cents or 0
                tip  = tip_cents  or 0
                tax  = tax_cents  or 0
                disc = disc_cents or 0
                # pm.amount_cents is post-discount; add disc back so CR Sales
                # reflects pre-discount revenue and DR Discounts shows the reduction
                gross_sales += sale - tax + disc
                tips        += tip
                taxes       += tax
                discounts   += disc
            elif etype == "REFUND":
                returns += abs(e_gross or 0)
            elif etype == "DEPOSIT_FEE":
                # Square instant/same-day deposit fee: negative gross, fee_cents=0
                fees += abs(e_gross or 0)

        # Build ordered line items
        lines = []

        lines.append(("DEBIT",  "clearing",       payout_net,   "Square deposit"))
        lines.append(("DEBIT",  "fees",           fees,         "Processing fees"))
        if discounts > 0:
            lines.append(("DEBIT", "discounts",   discounts,    "Discounts & comps"))
        if returns > 0:
            lines.append(("DEBIT", "returns",     returns,      "Returns & refunds"))
        lines.append(("CREDIT", "sales_revenue",  gross_sales,  "Gross sales"))
        if tips > 0:
            lines.append(("CREDIT", "tips",       tips,         "Tips"))
        if taxes > 0:
            lines.append(("CREDIT", "sales_tax",  taxes,        "Sales tax collected"))

        # Verify balance
        total_dr = sum(amt for (d, _, amt, _) in lines if d == "DEBIT")
        total_cr = sum(amt for (d, _, amt, _) in lines if d == "CREDIT")
        balanced = abs(total_dr - total_cr) <= 1  # allow 1 cent rounding

        # Upsert journal entry
        conn.execute("""
            INSERT OR REPLACE INTO journal_entries
                (payout_id, arrival_date, status,
                 payout_net_cents, gross_sales_cents, tips_cents,
                 taxes_cents, discounts_cents, returns_cents, fees_cents,
                 built_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            payout_id, arrival_date,
            "staged" if balanced else "error",
            payout_net, gross_sales, tips,
            taxes, discounts, returns, fees,
            datetime.now(timezone.utc).isoformat(),
        ))

        # Replace line items
        conn.execute("DELETE FROM journal_entry_lines WHERE payout_id = ?", (payout_id,))
        for order, (direction, acct_key, amount_cents, desc) in enumerate(lines):
            acct_id = WAVE_ACCOUNTS.get(acct_key, "")
            conn.execute("""
                INSERT INTO journal_entry_lines
                    (payout_id, line_order, direction, account_id, account_name,
                     amount_cents, description)
                VALUES (?,?,?,?,?,?,?)
            """, (
                payout_id, order, direction, acct_id,
                ACCOUNT_NAMES.get(acct_id, acct_key),
                amount_cents, desc,
            ))

        if not balanced:
            print(f"  [warn] {arrival_date}  UNBALANCED  "
                  f"DR={total_dr/100:.2f}  CR={total_cr/100:.2f}")
        built += 1

    conn.commit()
    return built


# ── Review entries ────────────────────────────────────────────────────────────
def review_entries(conn: sqlite3.Connection, begin_date: str, end_date: str,
                   status_filter: str = None) -> None:
    where = "WHERE je.arrival_date BETWEEN ? AND ?"
    params = [begin_date, end_date]
    if status_filter:
        where += " AND je.status = ?"
        params.append(status_filter)

    entries = conn.execute(f"""
        SELECT je.payout_id, je.arrival_date, je.status,
               je.payout_net_cents, je.gross_sales_cents,
               je.tips_cents, je.taxes_cents, je.fees_cents,
               je.wave_entry_id, je.error_msg
        FROM journal_entries je
        {where}
        ORDER BY je.arrival_date
    """, params).fetchall()

    if not entries:
        print("  No entries found for this range/status.")
        return

    for (pid, arr_date, status, net, gross, tips,
         taxes, fees, wave_id, err) in entries:

        status_tag = f"[{status.upper()}]"
        wave_tag   = f"  Wave: {wave_id}" if wave_id else ""
        err_tag    = f"  ERROR: {err}"    if err    else ""
        print(f"\n  {status_tag:<10} {arr_date}  ${net/100:.2f}  {pid[:16]}{wave_tag}{err_tag}")

        lines = conn.execute("""
            SELECT direction, account_name, amount_cents, description
            FROM journal_entry_lines
            WHERE payout_id = ?
            ORDER BY line_order
        """, (pid,)).fetchall()

        total_dr = total_cr = 0
        for direction, acct_name, amount_cents, desc in lines:
            side = "DR" if direction == "DEBIT" else "CR"
            print(f"    {side}  {acct_name:<35} ${amount_cents/100:>10.2f}  {desc}")
            if direction == "DEBIT":
                total_dr += amount_cents
            else:
                total_cr += amount_cents

        bal = "BALANCED" if abs(total_dr - total_cr) <= 1 else "** UNBALANCED **"
        print(f"    {'':40} DR=${total_dr/100:.2f}  CR=${total_cr/100:.2f}  {bal}")


# ── Status summary ────────────────────────────────────────────────────────────
def print_status(conn: sqlite3.Connection) -> None:
    print("\n  Journal entry status:")
    for row in conn.execute("""
        SELECT status, COUNT(*) as n, SUM(payout_net_cents) as total
        FROM journal_entries
        GROUP BY status ORDER BY status
    """).fetchall():
        print(f"    {row[0]:<10} {row[1]:>5} entries  ${row[2]/100:>12,.2f}")

    print("\n  Staged entries by month:")
    for row in conn.execute("""
        SELECT substr(arrival_date,1,7) as mo,
               COUNT(*) as n,
               SUM(payout_net_cents) as total
        FROM journal_entries
        WHERE status = 'staged'
        GROUP BY mo ORDER BY mo
    """).fetchall():
        print(f"    {row[0]}   {row[1]:>4} entries  ${row[2]/100:>12,.2f}")


# ── Post to Wave ──────────────────────────────────────────────────────────────
CREATE_TRANSACTION = """
mutation ($input: MoneyTransactionCreateInput!) {
  moneyTransactionCreate(input: $input) {
    didSucceed
    inputErrors { code message path }
    transaction { id }
  }
}
"""


def post_entry(conn: sqlite3.Connection, payout_id: str, arrival_date: str,
               payout_net_cents: int) -> bool:
    lines = conn.execute("""
        SELECT direction, account_id, amount_cents, description
        FROM journal_entry_lines
        WHERE payout_id = ?
        ORDER BY line_order
    """, (payout_id,)).fetchall()

    if not lines:
        return False

    line_items = []
    anchor = None

    for direction, acct_id, amount_cents, desc in lines:
        amount_str = f"{amount_cents / 100:.2f}"
        if direction == "DEBIT" and acct_id == WAVE_ACCOUNTS["clearing"] and anchor is None:
            # Clearing account leg becomes the anchor (DEPOSIT = DR to asset account)
            anchor = {
                "accountId": acct_id,
                "amount":    amount_str,
                "direction": "DEPOSIT",
            }
        else:
            line_items.append({
                "accountId":   acct_id,
                "amount":      amount_str,
                "balance":     direction,
                "description": desc,
            })

    if not anchor:
        print(f"    [error] No clearing anchor line found for {payout_id[:16]}")
        return False

    result = wave_gql(CREATE_TRANSACTION, {
        "input": {
            "businessId":  WAVE_BUSINESS_ID,
            "externalId":  f"{payout_id}:clr",
            "date":        arrival_date,
            "description": f"Square Settlement {arrival_date}",
            "anchor":      anchor,
            "lineItems":   line_items,
        }
    })

    gql = (result.get("data") or {}).get("moneyTransactionCreate", {})

    if gql.get("didSucceed"):
        wave_id = (gql.get("transaction") or {}).get("id", "")
        conn.execute("""
            UPDATE journal_entries
            SET status = 'posted', wave_entry_id = ?, posted_at = ?
            WHERE payout_id = ?
        """, (wave_id, datetime.now(timezone.utc).isoformat(), payout_id))
        conn.commit()
        print(f"    [posted] {wave_id}")
        return True

    errors = gql.get("inputErrors") or result.get("errors") or []
    err_msg = json.dumps(errors)[:300]
    conn.execute("""
        UPDATE journal_entries SET status = 'error', error_msg = ?
        WHERE payout_id = ?
    """, (err_msg, payout_id))
    conn.commit()
    print(f"    [error] {err_msg}")
    return False


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] == "--introspect":
        if not WAVE_TOKEN:
            print("[error] Set WAVE_TOKEN env var first.")
            sys.exit(1)
        introspect_wave()
        return

    if args[0] == "--query-wave":
        if not WAVE_TOKEN or not WAVE_BUSINESS_ID:
            print("[error] Set WAVE_TOKEN and WAVE_BUSINESS_ID env vars first.")
            sys.exit(1)
        print("\nQuerying 10 most recent Wave transactions...")
        result = wave_gql(QUERY_RECENT_TRANSACTIONS, {"businessId": WAVE_BUSINESS_ID, "page": 1})
        if result.get("errors"):
            print("  GraphQL errors:", json.dumps(result["errors"], indent=2))
            return
        biz = (result.get("data") or {}).get("business")
        if not biz:
            print("  No business returned. Raw response:")
            print(json.dumps(result, indent=2)[:1000])
            return
        txns = biz.get("transactions") or {}
        edges = txns.get("edges") or []
        info  = txns.get("pageInfo") or {}
        print(f"  Page {info.get('currentPage')}/{info.get('totalPages')}  —  {len(edges)} transaction(s)\n")
        for e in edges:
            n = e.get("node", {})
            acct = (n.get("account") or {}).get("name", "?")
            print(f"  {n.get('date','?'):<12} {n.get('description',''):<35} "
                  f"{acct:<20} ${float(n.get('amount') or 0):>9.2f}  id={n.get('id','')[:20]}")
        return

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    # Parse command and date range
    command   = args[0] if args[0].startswith("--") else None
    date_args = [a for a in args if not a.startswith("--")]

    if len(date_args) == 2:
        begin_date, end_date = date_args
    elif len(date_args) == 1:
        begin_date = end_date = date_args[0]
    else:
        begin_date = "2025-01-01"
        end_date   = date.today().strftime("%Y-%m-%d")

    # ── --status ──────────────────────────────────────────────────────────────
    if command == "--status":
        print_status(conn)
        conn.close()
        return

    # ── --build ───────────────────────────────────────────────────────────────
    if command == "--build":
        required = ["clearing", "sales_revenue", "tips", "fees", "sales_tax"]
        missing = [k for k in required if not WAVE_ACCOUNTS.get(k)]
        if missing:
            print(f"[error] Missing Wave account env vars: {missing}")
            sys.exit(1)
        print(f"\nBuilding entries {begin_date} → {end_date}...")
        n = build_entries(conn, begin_date, end_date)
        print(f"  Built {n} journal entr{'y' if n == 1 else 'ies'} — status: staged")
        print(f"\n  Next: python post_to_wave.py --review {begin_date} {end_date}")
        conn.close()
        return

    # ── --review ──────────────────────────────────────────────────────────────
    if command == "--review":
        print(f"\nReview: {begin_date} → {end_date}")
        review_entries(conn, begin_date, end_date)
        print(f"\n  Next: python post_to_wave.py --post {begin_date} {end_date}")
        conn.close()
        return

    # ── --post ────────────────────────────────────────────────────────────────
    if command == "--post":
        if not WAVE_TOKEN or not WAVE_BUSINESS_ID:
            print("[error] Set WAVE_TOKEN and WAVE_BUSINESS_ID env vars first.")
            sys.exit(1)

        # Pre-flight: surface any entries already in Wave so the user can't
        # accidentally duplicate them. Wave would reject on externalId anyway,
        # but this gives a clear, early warning instead of an API error.
        already_posted = conn.execute("""
            SELECT payout_id, arrival_date, payout_net_cents, posted_at
            FROM journal_entries
            WHERE arrival_date BETWEEN ? AND ? AND status = 'posted'
            ORDER BY arrival_date
        """, (begin_date, end_date)).fetchall()

        if already_posted:
            print(f"\n  [!] {len(already_posted)} entr{'y' if len(already_posted)==1 else 'ies'} "
                  f"in this range already posted to Wave:")
            for pid, arr_date, net, posted_at in already_posted:
                ts = (posted_at or "")[:10]
                print(f"      {arr_date}  ${net/100:>8.2f}  (posted {ts})  {pid[:16]}")

        to_post = conn.execute("""
            SELECT payout_id, arrival_date, payout_net_cents
            FROM journal_entries
            WHERE arrival_date BETWEEN ? AND ? AND status = 'staged'
            ORDER BY arrival_date
        """, (begin_date, end_date)).fetchall()

        if not to_post:
            if already_posted:
                print(f"\n  All entries in this range are already in Wave. Nothing to do.")
            else:
                print(f"\n  No staged entries in range {begin_date} to {end_date}.")
                print(f"  Run --build first, or check --status.")
            conn.close()
            return

        if already_posted:
            print(f"\n  Proceeding with {len(to_post)} staged "
                  f"entr{'y' if len(to_post)==1 else 'ies'}...")
        else:
            print(f"\nPosting {len(to_post)} staged entr{'y' if len(to_post) == 1 else 'ies'} "
                  f"to Wave ({begin_date} to {end_date})...")

        posted = errors = 0
        for pid, arr_date, net in to_post:
            print(f"  {arr_date}  ${net/100:.2f}  {pid[:16]}")
            if post_entry(conn, pid, arr_date, net):
                posted += 1
            else:
                errors += 1

        print(f"\n  Posted: {posted}  |  Errors: {errors}")
        conn.close()
        return

    print(__doc__)
    conn.close()


if __name__ == "__main__":
    main()
