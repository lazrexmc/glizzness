"""db.py — Supabase client and dashboard status/variance queries."""

import os
from datetime import date

from supabase import create_client, Client

SUPABASE_URL = "https://ikhcbncnaojrndilmnnd.supabase.co"
_client: Client = None


def _get_secret(name: str) -> str:
    try:
        import streamlit as st
        val = st.secrets.get(name)
        if val:
            return str(val)
    except Exception:
        pass
    return os.environ.get(name, "")


def get_client() -> Client:
    global _client
    if _client is None:
        key = _get_secret("SUPABASE_SERVICE_KEY")
        if not key:
            raise RuntimeError("SUPABASE_SERVICE_KEY not set")
        _client = create_client(SUPABASE_URL, key)
    return _client


def _fetch_all_rows(sb, table: str, select: str = "*", **filters) -> list:
    """Paginate through a Supabase table, returning all rows."""
    rows = []
    page = 1000
    offset = 0
    while True:
        q = sb.table(table).select(select).range(offset, offset + page - 1)
        for col, val in filters.items():
            q = q.eq(col, val)
        r = q.execute()
        chunk = r.data or []
        rows.extend(chunk)
        if len(chunk) < page:
            break
        offset += page
    return rows


def get_dashboard_status() -> dict:
    """Return a snapshot dict used by the status cards and sync log panel."""
    sb = get_client()

    # ── Square ──────────────────────────────────────────────────────────────
    p_r = sb.table("payouts").select("arrival_date").order("arrival_date", desc=True).limit(1).execute()
    last_payout_date = p_r.data[0]["arrival_date"] if p_r.data else None
    days_since = (
        (date.today() - date.fromisoformat(last_payout_date)).days
        if last_payout_date else None
    )

    all_pids_r = sb.table("payouts").select("payout_id").execute()
    all_pids = {r["payout_id"] for r in (all_pids_r.data or [])}

    # ── Journal entries ──────────────────────────────────────────────────────
    je_r = sb.table("journal_entries").select("payout_id,status").execute()
    je_data = je_r.data or []
    je_pids = {r["payout_id"] for r in je_data}
    status_counts: dict = {}
    for r in je_data:
        s = r.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    unbuilt = len(all_pids - je_pids)
    staged  = status_counts.get("staged", 0)
    posted  = status_counts.get("posted", 0)
    errors  = status_counts.get("error", 0)

    # ── Loan ────────────────────────────────────────────────────────────────
    lp_r  = sb.table("loan_payments").select("payment_date").execute()
    lje_r = sb.table("loan_journal_entries").select("payment_date,status").execute()
    loan_dates  = {r["payment_date"] for r in (lp_r.data or [])}
    lje_posted  = {r["payment_date"] for r in (lje_r.data or []) if r.get("status") == "posted"}
    lje_staged  = {r["payment_date"] for r in (lje_r.data or []) if r.get("status") == "staged"}
    lje_errors  = {r["payment_date"] for r in (lje_r.data or []) if r.get("status") == "error"}
    unposted_loan = len(loan_dates - lje_posted)

    # ── Sync log ─────────────────────────────────────────────────────────────
    log_r = sb.table("sync_log").select("*").order("synced_at", desc=True).limit(20).execute()

    return {
        "square": {
            "last_payout_date": last_payout_date,
            "days_since_payout": days_since,
            "total_payouts": len(all_pids),
            "stale": days_since is None or days_since > 3,
        },
        "entries": {
            "unbuilt": unbuilt,
            "staged":  staged,
            "posted":  posted,
            "errors":  errors,
        },
        "wave": {
            "staged": staged,
            "posted": posted,
            "errors": errors,
        },
        "loan": {
            "unposted": unposted_loan,
            "staged":   len(lje_staged),
            "errors":   len(lje_errors),
        },
        "sync_log": log_r.data or [],
    }


def get_variances() -> list:
    """Return payouts where |payout_amount - sum(entry net)| > 5 cents."""
    sb = get_client()

    payouts_r = sb.table("payouts").select("payout_id,arrival_date,amount_cents").execute()
    payouts = {r["payout_id"]: r for r in (payouts_r.data or [])}

    # Paginate payout_entries — may exceed 1000 rows
    all_entries = _fetch_all_rows(sb, "payout_entries", "payout_id,net_cents")
    sums: dict = {}
    for e in all_entries:
        pid = e["payout_id"]
        sums[pid] = sums.get(pid, 0) + (e["net_cents"] or 0)

    results = []
    for pid, p in payouts.items():
        if pid not in sums:
            continue
        var = abs((p["amount_cents"] or 0) - sums[pid])
        if var > 5:
            results.append({
                "payout_id":      pid,
                "arrival_date":   p["arrival_date"],
                "payout_cents":   p["amount_cents"],
                "entries_cents":  sums[pid],
                "variance_cents": var,
            })
    results.sort(key=lambda x: -x["variance_cents"])
    return results
