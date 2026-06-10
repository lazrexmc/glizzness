#!/usr/bin/env python3
"""
post_loan_payments.py — Post Weenie Wagon loan payment splits to Wave.

Each $77.07 weekly bank withdrawal is split into principal (reduces The First
Weenie Wagon liability) and interest (Interest Expense), anchored on the
Weenie Wagon Loan Clearing account. Only processes payments after the cutoff
date — prior entries were already entered manually in Wave.

Workflow:
  1. python post_loan_payments.py --import   # load CSV into DB
  2. python post_loan_payments.py --build    # stage entries after cutoff
  3. python post_loan_payments.py --review   # inspect before touching Wave
  4. python post_loan_payments.py --post     # send to Wave
  5. In Wave: categorize each WEENIEWAGON-INTERNET bank withdrawal
              to "Weenie Wagon Loan Clearing" (one click each)

Other commands:
  python post_loan_payments.py --status

Env vars required:
  WAVE_TOKEN
  WAVE_BUSINESS_ID
  WAVE_WEENIE_CLEARING_ID      Weenie Wagon Loan Clearing (Other ST Asset)
  WAVE_WEENIE_NOTE_PAYABLE_ID  The First Weenie Wagon (Long-Term Liability)
  WAVE_INTEREST_EXPENSE_ID     Interest Expense

Cutoff: payments on or before 2025-05-13 were entered manually — skipped.
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

WAVE_ACCOUNTS = {
    "clearing":      os.environ.get("WAVE_WEENIE_CLEARING_ID",      ""),
    "note_payable":  os.environ.get("WAVE_WEENIE_NOTE_PAYABLE_ID",  ""),
    "interest":      os.environ.get("WAVE_INTEREST_EXPENSE_ID",     ""),
}

ACCOUNT_NAMES = {
    WAVE_ACCOUNTS.get("clearing"):     "Weenie Wagon Loan Clearing",
    WAVE_ACCOUNTS.get("note_payable"): "The First Weenie Wagon",
    WAVE_ACCOUNTS.get("interest"):     "Interest Expense",
}

WAVE_GQL = "https://gql.waveapps.com/graphql/public"
WAVE_HEADERS = {
    "Authorization": f"Bearer {WAVE_TOKEN}",
    "Content-Type":  "application/json",
}

DB_PATH = "glizzness.db"

# Payments on or before this date were entered manually in Wave — skip them.
MANUAL_CUTOFF = "2025-05-12"


# ── Database ──────────────────────────────────────────────────────────────────

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS loan_payments (
        payment_date   TEXT PRIMARY KEY,
        payment_type   TEXT,
        description    TEXT,
        amount         REAL,
        principal      REAL,
        interest       REAL,
        escrow         REAL,
        late_charge    REAL,
        balance        REAL,
        note           TEXT
    );

    CREATE TABLE IF NOT EXISTS loan_journal_entries (
        payment_date   TEXT PRIMARY KEY,
        status         TEXT NOT NULL DEFAULT 'staged',
        -- status: staged | posted | error
        amount         REAL,
        principal      REAL,
        interest       REAL,
        wave_entry_id  TEXT,
        posted_at      TEXT,
        error_msg      TEXT,
        built_at       TEXT
    );
    """)
    conn.commit()


# ── Import CSV ────────────────────────────────────────────────────────────────

def import_csv(conn: sqlite3.Connection, csv_path: str) -> int:
    """
    Import the lender's amortization CSV.
    Expected columns: Date, Type, Description, Amount, Principal,
                      Interest, Escrow, Late Charge, Balance, Note
    """
    if not os.path.exists(csv_path):
        print(f"  [error] File not found: {csv_path}")
        return 0

    inserted = skipped = 0
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_date = (row.get("Date") or row.get(" Date") or "").strip()
            if not raw_date:
                continue
            # Normalize M/D/YYYY → YYYY-MM-DD
            try:
                payment_date = datetime.strptime(raw_date, "%m/%d/%Y").strftime("%Y-%m-%d")
            except ValueError:
                continue

            def f(key):
                v = (row.get(key) or row.get(" " + key) or "0").strip()
                try:
                    return float(v)
                except ValueError:
                    return 0.0

            if conn.execute(
                "SELECT 1 FROM loan_payments WHERE payment_date = ?", (payment_date,)
            ).fetchone():
                skipped += 1
                continue

            conn.execute("""
                INSERT INTO loan_payments
                    (payment_date, payment_type, description, amount,
                     principal, interest, escrow, late_charge, balance, note)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                payment_date,
                (row.get("Type") or "").strip(),
                (row.get("Description") or "").strip(),
                f("Amount"), f("Principal"), f("Interest"),
                f("Escrow"), f("Late Charge"), f("Balance"),
                (row.get("Note") or "").strip(),
            ))
            inserted += 1

    conn.commit()
    print(f"  Imported {inserted} payments, skipped {skipped} duplicates.")
    return inserted


# ── Build entries ─────────────────────────────────────────────────────────────

def build_entries(conn: sqlite3.Connection) -> int:
    payments = conn.execute("""
        SELECT payment_date, amount, principal, interest
        FROM loan_payments
        WHERE payment_date > ?
        ORDER BY payment_date
    """, (MANUAL_CUTOFF,)).fetchall()

    built = 0
    for payment_date, amount, principal, interest in payments:
        existing = conn.execute(
            "SELECT status FROM loan_journal_entries WHERE payment_date = ?",
            (payment_date,)
        ).fetchone()
        if existing and existing[0] == "posted":
            print(f"  [skip] {payment_date}  already posted")
            continue

        # Verify balance
        balanced = abs((principal + interest) - amount) <= 0.01

        conn.execute("""
            INSERT OR REPLACE INTO loan_journal_entries
                (payment_date, status, amount, principal, interest, built_at)
            VALUES (?,?,?,?,?,?)
        """, (
            payment_date,
            "staged" if balanced else "error",
            amount, principal, interest,
            datetime.now(timezone.utc).isoformat(),
        ))

        if not balanced:
            print(f"  [warn] {payment_date}  UNBALANCED  "
                  f"principal={principal:.2f} interest={interest:.2f} total={amount:.2f}")
        built += 1

    conn.commit()
    return built


# ── Review ────────────────────────────────────────────────────────────────────

def review_entries(conn: sqlite3.Connection) -> None:
    rows = conn.execute("""
        SELECT payment_date, status, amount, principal, interest,
               wave_entry_id, error_msg
        FROM loan_journal_entries
        ORDER BY payment_date
    """).fetchall()

    if not rows:
        print("  No entries — run --build first.")
        return

    for payment_date, status, amount, principal, interest, wave_id, err in rows:
        wave_tag = f"  Wave: {wave_id}" if wave_id else ""
        err_tag  = f"  ERROR: {err}"    if err    else ""
        print(f"\n  [{status.upper():<8}] {payment_date}  ${amount:.2f}{wave_tag}{err_tag}")
        clr_name  = ACCOUNT_NAMES.get(WAVE_ACCOUNTS.get("clearing"),     "Weenie Wagon Loan Clearing")
        note_name = ACCOUNT_NAMES.get(WAVE_ACCOUNTS.get("note_payable"), "The First Weenie Wagon")
        int_name  = ACCOUNT_NAMES.get(WAVE_ACCOUNTS.get("interest"),     "Interest Expense")
        print(f"    Tx1 (interest):   CR {clr_name} (anchor WITHDRAWAL ${interest:.2f})")
        print(f"                      DR {int_name} ${interest:.2f}")
        print(f"    Tx2 (principal):  DR {note_name} (anchor WITHDRAWAL ${principal:.2f})")
        print(f"                      CR {clr_name} ${principal:.2f}")


# ── Status ────────────────────────────────────────────────────────────────────

def print_status(conn: sqlite3.Connection) -> None:
    n_payments = conn.execute(
        "SELECT COUNT(*) FROM loan_payments WHERE payment_date > ?", (MANUAL_CUTOFF,)
    ).fetchone()[0]
    print(f"\n  loan_payments after {MANUAL_CUTOFF}: {n_payments}")

    for row in conn.execute("""
        SELECT status, COUNT(*), SUM(amount), SUM(principal), SUM(interest)
        FROM loan_journal_entries
        GROUP BY status ORDER BY status
    """).fetchall():
        print(f"  {row[0]:<10} {row[1]:>3} entries  "
              f"total=${row[2]:>8.2f}  principal=${row[3]:>8.2f}  interest=${row[4]:>8.2f}")

    # Running balance
    last = conn.execute(
        "SELECT payment_date, balance FROM loan_payments ORDER BY payment_date DESC LIMIT 1"
    ).fetchone()
    if last:
        print(f"\n  Latest balance: ${last[1]:,.2f}  ({last[0]})")


# ── Wave API ──────────────────────────────────────────────────────────────────

CREATE_TRANSACTION = """
mutation ($input: MoneyTransactionCreateInput!) {
  moneyTransactionCreate(input: $input) {
    didSucceed
    inputErrors { code message path }
    transaction { id }
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
        print(f"  [Wave HTTP {resp.status_code}] {resp.text[:400]}")
        resp.raise_for_status()
    return resp.json()


def post_entry(conn: sqlite3.Connection, payment_date: str,
               amount: float, principal: float, interest: float) -> bool:
    """
    Wave's moneyTransactionCreate does not allow liability accounts as line items.
    Split into two transactions:
      1. Interest:   Weenie Wagon Loan Clearing (WITHDRAWAL) → Interest Expense (DEBIT)
      2. Principal:  The First Weenie Wagon liability (WITHDRAWAL) → Loan Clearing (CREDIT)
    Clearing account nets to $0: bank import DR $77.07, API CR $interest + CR $principal.
    """

    # ── Transaction 1: Interest expense ──────────────────────────────────────
    # Skip if already posted (externalId collision means Wave already has it).
    r1 = wave_gql(CREATE_TRANSACTION, {
        "input": {
            "businessId":  WAVE_BUSINESS_ID,
            "externalId":  f"weenie-interest-{payment_date}",
            "date":        payment_date,
            "description": f"Weenie Wagon Loan Interest {payment_date}",
            "anchor": {
                "accountId": WAVE_ACCOUNTS["clearing"],
                "amount":    f"{interest:.2f}",
                "direction": "WITHDRAWAL",
            },
            "lineItems": [{
                "accountId":   WAVE_ACCOUNTS["interest"],
                "amount":      f"{interest:.2f}",
                "balance":     "DEBIT",
                "description": "Loan interest",
            }],
        }
    })
    gql1 = (r1.get("data") or {}).get("moneyTransactionCreate", {})
    interest_wave_id = (gql1.get("transaction") or {}).get("id", "")
    if gql1.get("didSucceed"):
        print(f"    [interest ok] ${interest:.2f}  {interest_wave_id}")
    else:
        errors = gql1.get("inputErrors") or r1.get("errors") or []
        # externalId already exists → interest was posted in a prior run; extract the id
        already = any(
            (e.get("code") or "").upper() in ("DUPLICATE", "ALREADY_EXISTS")
            or "already" in (e.get("message") or "").lower()
            or "duplicate" in (e.get("message") or "").lower()
            for e in errors
        )
        if already:
            print(f"    [interest already posted] ${interest:.2f} (skipping)")
        else:
            err_msg = f"interest tx: {json.dumps(errors)[:260]}"
            conn.execute(
                "UPDATE loan_journal_entries SET status='error', error_msg=? WHERE payment_date=?",
                (err_msg, payment_date),
            )
            conn.commit()
            print(f"    [error-interest] {err_msg}")
            return False

    # ── Transaction 2: Principal (reduce liability) ───────────────────────────
    # Anchor on the LIABILITY with DEPOSIT direction.
    # Wave treats DEPOSIT-into-loan as the payment direction:
    #   DEPOSIT → DR liability (reduces balance), WITHDRAWAL → CR liability (draws more).
    # The CREDIT line item on the clearing asset offsets the bank import DR.
    r2 = wave_gql(CREATE_TRANSACTION, {
        "input": {
            "businessId":  WAVE_BUSINESS_ID,
            "externalId":  f"weenie-principal-{payment_date}",
            "date":        payment_date,
            "description": f"Weenie Wagon Loan Principal {payment_date}",
            "anchor": {
                "accountId": WAVE_ACCOUNTS["note_payable"],
                "amount":    f"{principal:.2f}",
                "direction": "DEPOSIT",
            },
            "lineItems": [{
                "accountId":   WAVE_ACCOUNTS["clearing"],
                "amount":      f"{principal:.2f}",
                "balance":     "CREDIT",
                "description": "Loan principal",
            }],
        }
    })
    gql2 = (r2.get("data") or {}).get("moneyTransactionCreate", {})
    if not gql2.get("didSucceed"):
        errors  = gql2.get("inputErrors") or r2.get("errors") or []
        err_msg = f"principal tx: {json.dumps(errors)[:260]}"
        conn.execute(
            "UPDATE loan_journal_entries SET status='error', error_msg=? WHERE payment_date=?",
            (err_msg, payment_date),
        )
        conn.commit()
        print(f"    [error-principal] {err_msg}")
        return False
    principal_wave_id = (gql2.get("transaction") or {}).get("id", "")
    print(f"    [principal ok] ${principal:.2f}  {principal_wave_id}")

    wave_ids = f"int:{interest_wave_id}|pri:{principal_wave_id}"
    conn.execute("""
        UPDATE loan_journal_entries
        SET status = 'posted', wave_entry_id = ?, posted_at = ?
        WHERE payment_date = ?
    """, (wave_ids, datetime.now(timezone.utc).isoformat(), payment_date))
    conn.commit()
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

CSV_PATH = "Weenie Wagon Transactions 6.9.26.csv"


def main() -> None:
    args = sys.argv[1:]
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    if not args:
        print(__doc__)
        conn.close()
        return

    if args[0] == "--import":
        path = args[1] if len(args) > 1 else CSV_PATH
        import_csv(conn, path)
        print_status(conn)
        conn.close()
        return

    if args[0] == "--build":
        required = [k for k, v in WAVE_ACCOUNTS.items() if not v]
        if required:
            print(f"[error] Missing env vars: {['WAVE_WEENIE_CLEARING_ID' if k=='clearing' else 'WAVE_WEENIE_NOTE_PAYABLE_ID' if k=='note_payable' else 'WAVE_INTEREST_EXPENSE_ID' for k in required]}")
            sys.exit(1)
        n = build_entries(conn)
        print(f"  Built {n} entr{'y' if n==1 else 'ies'}.")
        print(f"\n  Next: python post_loan_payments.py --review")
        conn.close()
        return

    if args[0] == "--review":
        review_entries(conn)
        print(f"\n  Next: python post_loan_payments.py --post")
        conn.close()
        return

    if args[0] == "--status":
        print_status(conn)
        conn.close()
        return

    if args[0] == "--post":
        if not WAVE_TOKEN or not WAVE_BUSINESS_ID:
            print("[error] Set WAVE_TOKEN and WAVE_BUSINESS_ID env vars first.")
            sys.exit(1)
        missing = [k for k, v in WAVE_ACCOUNTS.items() if not v]
        if missing:
            print(f"[error] Missing Wave account env vars: {missing}")
            sys.exit(1)

        to_post = conn.execute("""
            SELECT payment_date, amount, principal, interest
            FROM loan_journal_entries
            WHERE status IN ('staged', 'error')
            ORDER BY payment_date
        """).fetchall()

        print(f"\nPosting {len(to_post)} staged loan payment(s) to Wave...")
        posted = errors = 0
        for payment_date, amount, principal, interest in to_post:
            print(f"  {payment_date}  ${amount:.2f}  (principal=${principal:.2f}  interest=${interest:.2f})")
            if post_entry(conn, payment_date, amount, principal, interest):
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
