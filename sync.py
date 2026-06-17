"""sync.py — Supabase-backed sync functions for the Glizzness dashboard.

Each function accepts a `log` callable for live progress output and returns
a summary dict. Secrets are read from Streamlit secrets or environment vars.
The original CLI scripts (sync_square.py, post_to_wave.py, etc.) still work
unchanged with the local SQLite database.
"""

import csv
import io
import os
import json
import re
import time
import requests
from datetime import date, datetime, timedelta, timezone
from typing import Callable

from db import get_client

SQUARE_BASE        = "https://connect.squareup.com/v2"
WAVE_GQL           = "https://gql.waveapps.com/graphql/public"
MANUAL_LOAN_CUTOFF = "2025-05-12"


# ── Secret / env helper ────────────────────────────────────────────────────────

def _get_secret(name: str) -> str:
    try:
        import streamlit as st
        val = st.secrets.get(name)
        if val:
            return str(val)
    except Exception:
        pass
    return os.environ.get(name, "")


# ── Account dicts ──────────────────────────────────────────────────────────────

def _wave_accounts() -> dict:
    return {
        "clearing":      _get_secret("WAVE_CLEARING_ACCOUNT_ID"),
        "bank":          _get_secret("WAVE_BANK_ACCOUNT_ID"),
        "sales_revenue": _get_secret("WAVE_SALES_REVENUE_ID"),
        "tips":          _get_secret("WAVE_TIPS_INCOME_ID"),
        "fees":          _get_secret("WAVE_PROCESSING_FEES_ID"),
        "sales_tax":     _get_secret("WAVE_SALES_TAX_ID"),
        "returns":       _get_secret("WAVE_SALES_RETURNS_ID"),
        "discounts":     _get_secret("WAVE_DISCOUNTS_ID"),
    }


def _loan_accounts() -> dict:
    return {
        "clearing":     _get_secret("WAVE_WEENIE_CLEARING_ID"),
        "note_payable": _get_secret("WAVE_WEENIE_NOTE_PAYABLE_ID"),
        "interest":     _get_secret("WAVE_INTEREST_EXPENSE_ID"),
    }


# ── Square API helpers ─────────────────────────────────────────────────────────

def _sq_headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_secret('SQUARE_TOKEN')}",
        "Square-Version": "2025-01-23",
        "Content-Type": "application/json",
    }


def _sq_get(path: str, params: dict = None, log: Callable = print) -> dict:
    resp = requests.get(
        f"{SQUARE_BASE}{path}",
        headers=_sq_headers(),
        params=params or {},
    )
    if not resp.ok:
        log(f"  [Square HTTP {resp.status_code}] {path} → {resp.text[:200]}")
        resp.raise_for_status()
    return resp.json()


def _fetch_payouts_sq(begin_date: str, end_date: str, log: Callable) -> list:
    """Fetch PAID/SENT payouts in arrival_date range. 7-day wider API window."""
    fetch_begin = (
        datetime.strptime(begin_date, "%Y-%m-%d").date() - timedelta(days=7)
    ).strftime("%Y-%m-%d")
    result, cursor = [], None
    log(f"  Fetching payouts ({begin_date} → {end_date})...")
    while True:
        params = {
            "begin_time": f"{fetch_begin}T00:00:00Z",
            "end_time":   f"{end_date}T23:59:59Z",
            "sort_order": "ASC",
            "limit":      100,
        }
        if cursor:
            params["cursor"] = cursor
        data = _sq_get("/payouts", params, log)
        for p in data.get("payouts", []):
            if p.get("status") not in ("PAID", "SENT"):
                continue
            if begin_date <= p.get("arrival_date", "") <= end_date:
                result.append(p)
        cursor = data.get("cursor")
        if not cursor:
            break
        time.sleep(0.1)
    log(f"  → {len(result)} payout(s)")
    return result


def _fetch_entries_sq(payout_id: str) -> list:
    entries, cursor = [], None
    while True:
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        data = _sq_get(f"/payouts/{payout_id}/payout-entries", params)
        entries.extend(data.get("payout_entries", []))
        cursor = data.get("cursor")
        if not cursor:
            break
        time.sleep(0.05)
    return entries


def _fetch_payments_sq(begin_date: str, end_date: str, log: Callable) -> list:
    result, cursor = [], None
    log(f"  Fetching payments ({begin_date} → {end_date})...")
    while True:
        params = {
            "begin_time": f"{begin_date}T00:00:00Z",
            "end_time":   f"{end_date}T23:59:59Z",
            "limit":      100,
        }
        if cursor:
            params["cursor"] = cursor
        data = _sq_get("/payments", params, log)
        for p in data.get("payments", []):
            if p.get("status") == "COMPLETED":
                result.append(p)
        cursor = data.get("cursor")
        if not cursor:
            break
        time.sleep(0.1)
    log(f"  → {len(result)} payment(s)")
    return result


def _fetch_order_sq(order_id: str, log: Callable) -> dict:
    try:
        return _sq_get(f"/orders/{order_id}", log=log).get("order", {})
    except Exception as e:
        log(f"    [warn] order {order_id}: {e}")
        return {}


# ── Record builders (Square JSON → Supabase row dict) ─────────────────────────

def _payout_rec(p: dict) -> dict:
    return {
        "payout_id":      p["id"],
        "status":         p.get("status"),
        "arrival_date":   p.get("arrival_date"),
        "created_at":     p.get("created_at"),
        "updated_at":     p.get("updated_at"),
        "amount_cents":   (p.get("amount_money") or {}).get("amount", 0),
        "currency":       (p.get("amount_money") or {}).get("currency", "USD"),
        "location_id":    p.get("location_id"),
        "destination_id": (p.get("destination") or {}).get("id"),
        "raw_json":       json.dumps(p),
    }


def _entry_rec(e: dict, payout_id: str) -> dict:
    details = e.get("type_charge_details") or e.get("type_refund_details") or {}
    return {
        "entry_id":     e["id"],
        "payout_id":    payout_id,
        "effective_at": e.get("effective_at"),
        "type":         e.get("type"),
        "gross_cents":  (e.get("gross_amount_money") or {}).get("amount", 0),
        "fee_cents":    (e.get("fee_amount_money")   or {}).get("amount", 0),
        "net_cents":    (e.get("net_amount_money")   or {}).get("amount", 0),
        "payment_id":   details.get("payment_id"),
        "raw_json":     json.dumps(e),
    }


def _payment_rec(p: dict) -> dict:
    fee = sum(
        (f.get("amount_money") or {}).get("amount", 0)
        for f in p.get("processing_fee", [])
    )
    return {
        "payment_id":     p["id"],
        "order_id":       p.get("order_id"),
        "created_at":     p.get("created_at"),
        "updated_at":     p.get("updated_at"),
        "status":         p.get("status"),
        "source_type":    p.get("source_type"),
        "delay_duration": p.get("delay_duration"),
        "amount_cents":   (p.get("amount_money")  or {}).get("amount", 0),
        "tip_cents":      (p.get("tip_money")     or {}).get("amount", 0),
        "total_cents":    (p.get("total_money")   or {}).get("amount", 0),
        "fee_cents":      fee,
        "square_product": (p.get("application_details") or {}).get("square_product", ""),
        "location_id":    p.get("location_id"),
        "raw_json":       json.dumps(p),
    }


def _order_rec(o: dict) -> dict:
    net_amounts = o.get("net_amounts") or {}
    return {
        "order_id":                   o["id"],
        "state":                      o.get("state"),
        "created_at":                 o.get("created_at"),
        "updated_at":                 o.get("updated_at"),
        "location_id":                o.get("location_id"),
        "total_money_cents":          (o.get("total_money")           or {}).get("amount", 0),
        "total_tax_cents":            (o.get("total_tax_money")       or {}).get("amount", 0),
        "total_discount_cents":       (o.get("total_discount_money")  or {}).get("amount", 0),
        "total_tip_cents":            (o.get("total_tip_money")       or {}).get("amount", 0),
        "total_service_charge_cents": (o.get("total_service_charge_money") or {}).get("amount", 0),
        "net_total_cents":            (net_amounts.get("total_money") or {}).get("amount", 0),
        "raw_json":                   json.dumps(o),
    }


# ── Supabase batch helpers ─────────────────────────────────────────────────────

def _upsert(sb, table: str, records: list, batch_size: int = 500) -> None:
    for i in range(0, len(records), batch_size):
        sb.table(table).upsert(records[i:i + batch_size]).execute()


def _existing_ids(sb, table: str, pk_col: str, ids: list) -> set:
    found = set()
    for i in range(0, len(ids), 150):
        batch = ids[i:i + 150]
        r = sb.table(table).select(pk_col).in_(pk_col, batch).execute()
        found.update(row[pk_col] for row in (r.data or []))
    return found


# ══════════════════════════════════════════════════════════════════════════════
# Public sync functions
# ══════════════════════════════════════════════════════════════════════════════

def sync_square(begin_date: str = None, end_date: str = None,
                log: Callable = print) -> dict:
    """Sync Square payouts, payout entries, payments, and orders to Supabase."""
    if not _get_secret("SQUARE_TOKEN"):
        raise RuntimeError("SQUARE_TOKEN not set")

    sb = get_client()
    if not begin_date:
        begin_date = f"{date.today().year}-01-01"
    if not end_date:
        end_date = date.today().strftime("%Y-%m-%d")

    log(f"Square sync: {begin_date} → {end_date}")

    # 1. Payouts — deduplicate by id (Square can return the same payout on multiple pages)
    payouts = list({p["id"]: p for p in _fetch_payouts_sq(begin_date, end_date, log)}.values())
    if payouts:
        _upsert(sb, "payouts", [_payout_rec(p) for p in payouts])

    # 2. Payout entries — only for payouts not yet in the entries table
    range_pids = [p["id"] for p in payouts]
    if range_pids:
        existing_entry_pids = _existing_ids(sb, "payout_entries", "payout_id", range_pids)
        need_entries = [pid for pid in range_pids if pid not in existing_entry_pids]
    else:
        need_entries = []

    log(f"  Fetching payout entries for {len(need_entries)} payout(s)...")
    total_entries = 0
    entry_buf = []
    for i, pid in enumerate(need_entries, 1):
        raw_entries = _fetch_entries_sq(pid)
        entry_buf.extend(_entry_rec(e, pid) for e in raw_entries)
        total_entries += len(raw_entries)
        if len(entry_buf) >= 500:
            _upsert(sb, "payout_entries", entry_buf)
            entry_buf = []
            log(f"    {i}/{len(need_entries)} payouts processed...")
    if entry_buf:
        _upsert(sb, "payout_entries", entry_buf)
    log(f"  → {total_entries} payout entr{'y' if total_entries == 1 else 'ies'}")

    # 3. Payments — date-range pull, deduplicated
    pay_begin = (
        datetime.strptime(begin_date, "%Y-%m-%d").date() - timedelta(days=8)
    ).strftime("%Y-%m-%d")
    payments = list({p["id"]: p for p in _fetch_payments_sq(pay_begin, end_date, log)}.values())
    if payments:
        _upsert(sb, "payments", [_payment_rec(p) for p in payments])

    # 4. Orders — only missing ones
    all_pay_r = sb.table("payments").select("order_id").execute()
    all_order_ids = list({
        r["order_id"] for r in (all_pay_r.data or []) if r.get("order_id")
    })
    existing_order_ids = _existing_ids(sb, "orders", "order_id", all_order_ids)
    missing_orders = [oid for oid in all_order_ids if oid not in existing_order_ids]

    log(f"  Fetching {len(missing_orders)} new order(s)...")
    order_buf = []
    for i, oid in enumerate(missing_orders, 1):
        o = _fetch_order_sq(oid, log)
        if o and o.get("id"):
            order_buf.append(_order_rec(o))
        if len(order_buf) >= 100:
            _upsert(sb, "orders", order_buf)
            order_buf = []
        if i % 25 == 0:
            log(f"    {i}/{len(missing_orders)} orders...")
        time.sleep(0.05)
    if order_buf:
        _upsert(sb, "orders", order_buf)

    # 5. Sync log
    sb.table("sync_log").insert({
        "synced_at":      datetime.now(timezone.utc).isoformat(),
        "date_range":     f"{begin_date}/{end_date}",
        "payouts_found":  len(payouts),
        "entries_found":  total_entries,
        "payments_found": len(payments),
        "orders_found":   len(missing_orders),
        "errors":         "[]",
    }).execute()

    summary = {
        "payouts":  len(payouts),
        "entries":  total_entries,
        "payments": len(payments),
        "orders":   len(missing_orders),
    }
    log(f"  Square sync complete — {summary}")
    return summary


# ── Wave GraphQL helper ────────────────────────────────────────────────────────

_CREATE_TXN_GQL = """
mutation ($input: MoneyTransactionCreateInput!) {
  moneyTransactionCreate(input: $input) {
    didSucceed
    inputErrors { code message path }
    transaction { id }
  }
}
"""


def _wave_gql(variables: dict, log: Callable = print) -> dict:
    resp = requests.post(
        WAVE_GQL,
        headers={
            "Authorization": f"Bearer {_get_secret('WAVE_TOKEN')}",
            "Content-Type": "application/json",
        },
        json={"query": _CREATE_TXN_GQL, "variables": variables},
    )
    if not resp.ok:
        log(f"  [Wave HTTP {resp.status_code}] {resp.text[:300]}")
        resp.raise_for_status()
    return resp.json()


def _already_posted(errors: list) -> bool:
    return any(
        (e.get("code") or "").upper() in ("DUPLICATE", "ALREADY_EXISTS")
        or "already" in (e.get("message") or "").lower()
        or "duplicate" in (e.get("message") or "").lower()
        for e in errors
    )


# ── Build Wave journal entries ─────────────────────────────────────────────────

def build_wave_entries(begin_date: str = None, end_date: str = None,
                       log: Callable = print) -> dict:
    """Compute journal entries from Square data and save to Supabase.

    Rebuilds staged/error entries. Skips entries already posted to Wave.
    """
    sb = get_client()
    accts = _wave_accounts()

    if not begin_date:
        begin_date = "2020-01-01"
    if not end_date:
        end_date = date.today().strftime("%Y-%m-%d")

    payouts_r = (
        sb.table("payouts")
        .select("payout_id,arrival_date,amount_cents")
        .gte("arrival_date", begin_date)
        .lte("arrival_date", end_date)
        .order("arrival_date")
        .execute()
    )
    payouts = payouts_r.data or []

    je_r = sb.table("journal_entries").select("payout_id,status").execute()
    posted_pids = {r["payout_id"] for r in (je_r.data or []) if r.get("status") == "posted"}
    to_build = [p for p in payouts if p["payout_id"] not in posted_pids]

    log(f"  Building entries for {len(to_build)} payout(s) (of {len(payouts)} in range)...")
    if not to_build:
        return {"built": 0, "warned": 0, "skipped": len(payouts)}

    # Batch-fetch payout entries for all payouts to build (paginated — Supabase caps at 1000/call)
    to_build_ids = [p["payout_id"] for p in to_build]
    all_raw_entries = []
    PAGE = 1000
    for i in range(0, len(to_build_ids), 50):
        batch = to_build_ids[i:i + 50]
        offset = 0
        while True:
            r = (
                sb.table("payout_entries")
                .select("payout_id,type,gross_cents,fee_cents,net_cents,payment_id")
                .in_("payout_id", batch)
                .range(offset, offset + PAGE - 1)
                .execute()
            )
            chunk = r.data or []
            all_raw_entries.extend(chunk)
            if len(chunk) < PAGE:
                break
            offset += PAGE

    entries_by_payout: dict = {}
    all_pay_ids: set = set()
    for e in all_raw_entries:
        entries_by_payout.setdefault(e["payout_id"], []).append(e)
        if e.get("payment_id"):
            all_pay_ids.add(e["payment_id"])

    # Batch-fetch payments (paginated)
    payments_map: dict = {}
    pay_id_list = list(all_pay_ids)
    for i in range(0, len(pay_id_list), 150):
        batch = pay_id_list[i:i + 150]
        offset = 0
        while True:
            r = (
                sb.table("payments")
                .select("payment_id,amount_cents,tip_cents,order_id")
                .in_("payment_id", batch)
                .range(offset, offset + PAGE - 1)
                .execute()
            )
            chunk = r.data or []
            for row in chunk:
                payments_map[row["payment_id"]] = row
            if len(chunk) < PAGE:
                break
            offset += PAGE

    # Batch-fetch orders (paginated)
    all_order_ids = list({p["order_id"] for p in payments_map.values() if p.get("order_id")})
    orders_map: dict = {}
    for i in range(0, len(all_order_ids), 150):
        batch = all_order_ids[i:i + 150]
        offset = 0
        while True:
            r = (
                sb.table("orders")
                .select("order_id,total_tax_cents,total_discount_cents")
                .in_("order_id", batch)
                .range(offset, offset + PAGE - 1)
                .execute()
            )
            chunk = r.data or []
            for row in chunk:
                orders_map[row["order_id"]] = row
            if len(chunk) < PAGE:
                break
            offset += PAGE

    built = warned = 0
    now = datetime.now(timezone.utc).isoformat()

    for payout in to_build:
        pid        = payout["payout_id"]
        arr_date   = payout["arrival_date"]
        payout_net = payout["amount_cents"] or 0

        entries = entries_by_payout.get(pid, [])
        if not entries:
            log(f"  [warn] {pid[:16]} {arr_date} — no entries (run Square sync first)")
            warned += 1
            continue

        gross_sales = tips = taxes = discounts = fees = returns = 0

        for e in entries:
            etype   = e.get("type", "")
            e_gross = e.get("gross_cents") or 0
            e_fee   = e.get("fee_cents")   or 0
            pay_id  = e.get("payment_id")

            pm    = payments_map.get(pay_id, {}) if pay_id else {}
            oid   = pm.get("order_id")
            order = orders_map.get(oid, {}) if oid else {}

            sale_c = pm.get("amount_cents")             or 0
            tip_c  = pm.get("tip_cents")                or 0
            tax_c  = order.get("total_tax_cents")       or 0
            disc_c = order.get("total_discount_cents")  or 0

            fees += e_fee
            if etype == "CHARGE":
                # Restore discount to show pre-discount gross revenue
                gross_sales += sale_c - tax_c + disc_c
                tips        += tip_c
                taxes       += tax_c
                discounts   += disc_c
            elif etype == "REFUND":
                returns += abs(e_gross)
            elif etype == "DEPOSIT_FEE":
                # Instant-deposit fee: negative gross, fee_cents=0
                fees += abs(e_gross)

        lines = [
            ("DEBIT",  "clearing",      payout_net,   "Square deposit"),
            ("DEBIT",  "fees",          fees,          "Processing fees"),
        ]
        if discounts > 0:
            lines.append(("DEBIT",  "discounts",    discounts,   "Discounts & comps"))
        if returns > 0:
            lines.append(("DEBIT",  "returns",      returns,     "Returns & refunds"))
        lines.append(("CREDIT", "sales_revenue",    gross_sales, "Gross sales"))
        if tips > 0:
            lines.append(("CREDIT", "tips",         tips,        "Tips"))
        if taxes > 0:
            lines.append(("CREDIT", "sales_tax",    taxes,       "Sales tax collected"))

        total_dr = sum(amt for d, _, amt, _ in lines if d == "DEBIT")
        total_cr = sum(amt for d, _, amt, _ in lines if d == "CREDIT")
        balanced = abs(total_dr - total_cr) <= 1

        sb.table("journal_entries").upsert({
            "payout_id":         pid,
            "arrival_date":      arr_date,
            "status":            "staged" if balanced else "error",
            "payout_net_cents":  payout_net,
            "gross_sales_cents": gross_sales,
            "tips_cents":        tips,
            "taxes_cents":       taxes,
            "discounts_cents":   discounts,
            "returns_cents":     returns,
            "fees_cents":        fees,
            "built_at":          now,
        }).execute()

        # Replace line items
        sb.table("journal_entry_lines").delete().eq("payout_id", pid).execute()
        line_records = [
            {
                "payout_id":    pid,
                "line_order":   i,
                "direction":    direction,
                "account_id":   accts.get(acct_key, ""),
                "account_name": acct_key,
                "amount_cents": amount_cents,
                "description":  desc,
            }
            for i, (direction, acct_key, amount_cents, desc) in enumerate(lines)
        ]
        sb.table("journal_entry_lines").insert(line_records).execute()

        if not balanced:
            log(f"  [warn] {arr_date} UNBALANCED DR={total_dr/100:.2f} CR={total_cr/100:.2f}")
        built += 1

    log(f"  Entries built: {built}  Warned: {warned}  Skipped (posted): {len(payouts) - len(to_build)}")
    return {"built": built, "warned": warned, "skipped": len(payouts) - len(to_build)}


# ── Post Wave journal entries ──────────────────────────────────────────────────

CLOSED_YEAR_CUTOFF = "2025-01-01"  # entries before this date must never be posted via API


def post_to_wave(begin_date: str = None, log: Callable = print) -> dict:
    """Post staged journal entries to Wave. Skips already-posted (by externalId).

    begin_date: only post entries on or after this date (default: CLOSED_YEAR_CUTOFF).
    2022-2024 books are closed — passing an earlier date is blocked by the cutoff floor.
    """
    if not _get_secret("WAVE_TOKEN") or not _get_secret("WAVE_BUSINESS_ID"):
        raise RuntimeError("WAVE_TOKEN and WAVE_BUSINESS_ID must be set")

    # Hard floor: never post closed-year transactions regardless of what the caller passes.
    effective_begin = begin_date or CLOSED_YEAR_CUTOFF
    if effective_begin < CLOSED_YEAR_CUTOFF:
        effective_begin = CLOSED_YEAR_CUTOFF
        log(f"  [guard] begin_date raised to {CLOSED_YEAR_CUTOFF} (closed-year floor)")

    sb    = get_client()
    accts = _wave_accounts()
    biz   = _get_secret("WAVE_BUSINESS_ID")

    staged_r = (
        sb.table("journal_entries")
        .select("payout_id,arrival_date,payout_net_cents")
        .in_("status", ["staged", "error"])
        .gte("arrival_date", effective_begin)
        .order("arrival_date")
        .execute()
    )
    to_post = staged_r.data or []
    log(f"  Posting {len(to_post)} journal entr{'y' if len(to_post) == 1 else 'ies'} to Wave (from {effective_begin})...")

    posted = errors = 0

    for je in to_post:
        pid      = je["payout_id"]
        arr_date = je["arrival_date"]

        lines_r = (
            sb.table("journal_entry_lines")
            .select("direction,account_id,amount_cents,description")
            .eq("payout_id", pid)
            .order("line_order")
            .execute()
        )
        lines = lines_r.data or []
        if not lines:
            log(f"  [skip] {pid[:16]} — no lines (rebuild entries first)")
            continue

        anchor = None
        line_items = []
        for ln in lines:
            amt = f"{(ln['amount_cents'] or 0) / 100:.2f}"
            if (
                ln["direction"] == "DEBIT"
                and ln["account_id"] == accts["clearing"]
                and anchor is None
            ):
                anchor = {"accountId": ln["account_id"], "amount": amt, "direction": "DEPOSIT"}
            else:
                line_items.append({
                    "accountId":   ln["account_id"],
                    "amount":      amt,
                    "balance":     ln["direction"],
                    "description": ln["description"],
                })

        if not anchor:
            err = "No clearing anchor line found"
            sb.table("journal_entries").update({"status": "error", "error_msg": err}).eq("payout_id", pid).execute()
            log(f"  [error] {pid[:16]} — {err}")
            errors += 1
            continue

        result = _wave_gql({
            "input": {
                "businessId":  biz,
                "externalId":  f"{pid}:clr",
                "date":        arr_date,
                "description": f"Square Settlement {arr_date}",
                "anchor":      anchor,
                "lineItems":   line_items,
            }
        }, log)

        gql = (result.get("data") or {}).get("moneyTransactionCreate", {})
        if gql.get("didSucceed"):
            wave_id = (gql.get("transaction") or {}).get("id", "")
            sb.table("journal_entries").update({
                "status":        "posted",
                "wave_entry_id": wave_id,
                "posted_at":     datetime.now(timezone.utc).isoformat(),
                "error_msg":     None,
            }).eq("payout_id", pid).execute()
            log(f"  [ok] {arr_date}  {wave_id}")
            posted += 1
        else:
            errs = gql.get("inputErrors") or result.get("errors") or []
            if _already_posted(errs):
                sb.table("journal_entries").update({
                    "status":    "posted",
                    "posted_at": datetime.now(timezone.utc).isoformat(),
                }).eq("payout_id", pid).execute()
                log(f"  [already posted] {arr_date}")
                posted += 1
            else:
                err_msg = json.dumps(errs)[:300]
                sb.table("journal_entries").update({"status": "error", "error_msg": err_msg}).eq("payout_id", pid).execute()
                log(f"  [error] {arr_date} — {err_msg}")
                errors += 1

    log(f"  Wave post complete — posted: {posted}  errors: {errors}")
    return {"posted": posted, "errors": errors}


# ── Build loan journal entries ─────────────────────────────────────────────────

def build_loan_entries(log: Callable = print) -> dict:
    """Stage loan journal entries for all payments after the manual cutoff."""
    sb = get_client()

    payments_r = (
        sb.table("loan_payments")
        .select("payment_date,amount,principal,interest")
        .gt("payment_date", MANUAL_LOAN_CUTOFF)
        .order("payment_date")
        .execute()
    )
    payments = payments_r.data or []

    lje_r = sb.table("loan_journal_entries").select("payment_date,status").execute()
    posted_dates = {r["payment_date"] for r in (lje_r.data or []) if r.get("status") == "posted"}

    built = skipped = 0
    now = datetime.now(timezone.utc).isoformat()

    for p in payments:
        pd = p["payment_date"]
        if pd in posted_dates:
            skipped += 1
            continue

        amt  = p.get("amount")    or 0.0
        prin = p.get("principal") or 0.0
        intr = p.get("interest")  or 0.0
        balanced = abs((prin + intr) - amt) <= 0.01

        sb.table("loan_journal_entries").upsert({
            "payment_date": pd,
            "status":       "staged" if balanced else "error",
            "amount":       amt,
            "principal":    prin,
            "interest":     intr,
            "built_at":     now,
        }).execute()

        if not balanced:
            log(f"  [warn] {pd} UNBALANCED principal={prin:.2f} interest={intr:.2f} total={amt:.2f}")
        built += 1

    log(f"  Loan entries built: {built}  Skipped (posted): {skipped}")
    return {"built": built, "skipped": skipped}


# ── Post loan payments to Wave ─────────────────────────────────────────────────

def post_loan_payments(log: Callable = print) -> dict:
    """Post staged loan journal entries to Wave (two transactions per payment)."""
    if not _get_secret("WAVE_TOKEN") or not _get_secret("WAVE_BUSINESS_ID"):
        raise RuntimeError("WAVE_TOKEN and WAVE_BUSINESS_ID must be set")

    sb    = get_client()
    accts = _loan_accounts()
    biz   = _get_secret("WAVE_BUSINESS_ID")

    staged_r = (
        sb.table("loan_journal_entries")
        .select("payment_date,amount,principal,interest")
        .in_("status", ["staged", "error"])
        .order("payment_date")
        .execute()
    )
    to_post = staged_r.data or []
    log(f"  Posting {len(to_post)} loan payment(s) to Wave...")

    posted = errors = 0

    for lp in to_post:
        pd   = lp["payment_date"]
        amt  = lp.get("amount")    or 0.0
        prin = lp.get("principal") or 0.0
        intr = lp.get("interest")  or 0.0

        # Transaction 1: Interest expense
        r1  = _wave_gql({"input": {
            "businessId":  biz,
            "externalId":  f"weenie-interest-{pd}",
            "date":        pd,
            "description": f"Weenie Wagon Loan Interest {pd}",
            "anchor":      {"accountId": accts["clearing"], "amount": f"{intr:.2f}", "direction": "WITHDRAWAL"},
            "lineItems":   [{"accountId": accts["interest"], "amount": f"{intr:.2f}", "balance": "DEBIT", "description": "Loan interest"}],
        }}, log)
        gql1 = (r1.get("data") or {}).get("moneyTransactionCreate", {})
        int_id = (gql1.get("transaction") or {}).get("id", "")

        if not gql1.get("didSucceed"):
            errs = gql1.get("inputErrors") or r1.get("errors") or []
            if not _already_posted(errs):
                err_msg = f"interest tx: {json.dumps(errs)[:200]}"
                sb.table("loan_journal_entries").update({"status": "error", "error_msg": err_msg}).eq("payment_date", pd).execute()
                log(f"  [error-interest] {pd} — {err_msg}")
                errors += 1
                continue
            log(f"  [interest already posted] {pd}")

        # Transaction 2: Principal (reduce liability)
        r2  = _wave_gql({"input": {
            "businessId":  biz,
            "externalId":  f"weenie-principal-{pd}",
            "date":        pd,
            "description": f"Weenie Wagon Loan Principal {pd}",
            "anchor":      {"accountId": accts["note_payable"], "amount": f"{prin:.2f}", "direction": "DEPOSIT"},
            "lineItems":   [{"accountId": accts["clearing"], "amount": f"{prin:.2f}", "balance": "CREDIT", "description": "Loan principal"}],
        }}, log)
        gql2 = (r2.get("data") or {}).get("moneyTransactionCreate", {})

        if not gql2.get("didSucceed"):
            errs = gql2.get("inputErrors") or r2.get("errors") or []
            err_msg = f"principal tx: {json.dumps(errs)[:200]}"
            sb.table("loan_journal_entries").update({"status": "error", "error_msg": err_msg}).eq("payment_date", pd).execute()
            log(f"  [error-principal] {pd} — {err_msg}")
            errors += 1
            continue

        pri_id = (gql2.get("transaction") or {}).get("id", "")
        sb.table("loan_journal_entries").update({
            "status":        "posted",
            "wave_entry_id": f"int:{int_id}|pri:{pri_id}",
            "posted_at":     datetime.now(timezone.utc).isoformat(),
            "error_msg":     None,
        }).eq("payment_date", pd).execute()
        log(f"  [ok] {pd}  ${amt:.2f}")
        posted += 1

    log(f"  Loan post complete — posted: {posted}  errors: {errors}")
    return {"posted": posted, "errors": errors}


# ── Close a calendar year ──────────────────────────────────────────────────────

def close_year(year: int, log: Callable = print) -> dict:
    """Mark all journal_entries for a calendar year as 'closed'.

    Closed entries are excluded from post_to_wave() queries and can never be
    posted again. Call this after a year's books are finalized in Wave.
    The hard floor in post_to_wave() (CLOSED_YEAR_CUTOFF) only covers years
    before 2025; closing later years via this function extends that protection.
    """
    sb = get_client()
    year_begin = f"{year}-01-01"
    next_begin = f"{year + 1}-01-01"

    r = (
        sb.table("journal_entries")
        .update({"status": "closed", "error_msg": f"Closed {year}"})
        .gte("arrival_date", year_begin)
        .lt("arrival_date", next_begin)
        .neq("status", "closed")
        .execute()
    )
    count = len(r.data or [])
    log(f"  {year}: {count} entr{'y' if count == 1 else 'ies'} marked closed")
    return {"closed": count, "year": year}


# ── Import Wave CSV ────────────────────────────────────────────────────────────

def import_wave_csv(file_content: str, source_name: str,
                    replace: bool = False, log: Callable = print) -> dict:
    """Parse a Wave CSV export and upsert rows into Supabase wave_transactions.

    Wave → Accounting → Transactions → Export → Transactions CSV.
    replace=True deletes all existing rows for this source_file before inserting,
    which applies any corrections made in Wave since the last import.
    row_key = date|description|account|debit|credit — exact duplicates are no-ops.
    """
    sb  = get_client()
    now = datetime.now(timezone.utc).isoformat()

    existing_r = (
        sb.table("wave_transactions")
        .select("row_key", count="exact")
        .eq("source_file", source_name)
        .execute()
    )
    existing_count = existing_r.count or 0

    if replace and existing_count:
        sb.table("wave_transactions").delete().eq("source_file", source_name).execute()
        log(f"  Cleared {existing_count} existing row(s) for '{source_name}'")
    elif existing_count:
        log(f"  '{source_name}' already has {existing_count} row(s) — exact duplicates will be skipped")

    # ── Parse CSV ──────────────────────────────────────────────────────────────
    # Wave CSV format: 4 metadata rows, then a header row, then data rows.
    # Account-name section header rows have a non-date value in the date column.

    f = io.StringIO(file_content)
    for _ in range(4):
        f.readline()

    reader = csv.DictReader(f)
    headers = reader.fieldnames or []
    col: dict = {}
    for h in headers:
        hl = h.lower().strip()
        if hl == "date":           col["date"]    = h
        elif hl == "description":  col["desc"]    = h
        elif "debit"   in hl:      col["debit"]   = h
        elif "credit"  in hl:      col["credit"]  = h
        elif "balance" in hl:      col["balance"] = h

    missing = [k for k in ("date", "desc", "debit", "credit") if k not in col]
    if missing:
        raise ValueError(f"Cannot map CSV columns {missing}. Found headers: {headers}")

    def _amt(val: str) -> float:
        v = (val or "").strip().replace(",", "").replace("$", "").replace("(", "-").replace(")", "")
        try:
            return float(v)
        except ValueError:
            return 0.0

    _is_date = re.compile(r"^\d{4}-\d{2}-\d{2}$").match

    current_account = ""
    rows: list = []

    for row in reader:
        date_cell   = (row.get(col["date"])   or "").strip()
        description = (row.get(col["desc"])   or "").strip()
        debit       = _amt(row.get(col["debit"],   ""))
        credit      = _amt(row.get(col["credit"],  ""))
        balance     = _amt(row.get(col.get("balance", ""), ""))

        if date_cell and not _is_date(date_cell):
            current_account = date_cell
            continue
        if not _is_date(date_cell):
            continue
        if description.lower() in ("starting balance", "ending balance", "total"):
            continue

        row_key = f"{date_cell}|{description}|{current_account}|{debit:.2f}|{credit:.2f}"
        rows.append({
            "row_key":      row_key,
            "txn_date":     date_cell,
            "description":  description,
            "account_name": current_account,
            "debit":        debit,
            "credit":       credit,
            "balance":      balance,
            "direction":    "CREDIT" if credit > 0 else "DEBIT",
            "net_amount":   credit - debit,
            "imported_at":  now,
            "source_file":  source_name,
        })

    if not rows:
        log("  No data rows found in CSV")
        return {"upserted": 0, "source": source_name}

    _upsert(sb, "wave_transactions", rows)
    log(f"  Upserted {len(rows)} row(s) from '{source_name}' into wave_transactions")
    return {"upserted": len(rows), "source": source_name}
