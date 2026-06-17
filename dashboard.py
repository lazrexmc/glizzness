"""dashboard.py — Glizzness Operations Dashboard

Run locally:
    streamlit run dashboard.py

Secrets (via .streamlit/secrets.toml locally, or Streamlit Cloud secrets):
    APP_PASSWORD, SUPABASE_SERVICE_KEY, SQUARE_TOKEN,
    WAVE_TOKEN, WAVE_BUSINESS_ID, plus all WAVE_*_ID account vars.
"""

import streamlit as st
from datetime import date

st.set_page_config(
    page_title="Glizzness Dashboard",
    page_icon="🌭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Password gate ──────────────────────────────────────────────────────────────

APP_PASSWORD = ""
try:
    APP_PASSWORD = st.secrets.get("APP_PASSWORD", "")
except Exception:
    pass

if APP_PASSWORD:
    if not st.session_state.get("authenticated"):
        st.title("🌭 Glizzness Dashboard")
        pw = st.text_input("Password", type="password")
        if st.button("Login", type="primary"):
            if pw == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password")
        st.stop()

# ── Header ─────────────────────────────────────────────────────────────────────

st.title("🌭 Glizzness Operations Dashboard")
st.caption("The Glizzness LLC — Square → Wave sync status and controls")

# ── Import sync modules (after secrets are available) ─────────────────────────

try:
    from db import get_dashboard_status, get_variances
    from sync import (
        sync_square, build_wave_entries, post_to_wave,
        build_loan_entries, post_loan_payments, close_year,
    )
    modules_ok = True
except Exception as e:
    st.error(f"Import error: {e}")
    modules_ok = False

# ── Session state defaults ────────────────────────────────────────────────────

if "run_log" not in st.session_state:
    st.session_state.run_log = []
if "status" not in st.session_state:
    st.session_state.status = None
if "status_error" not in st.session_state:
    st.session_state.status_error = None

# ── Load / refresh status ─────────────────────────────────────────────────────

top_col1, top_col2 = st.columns([6, 1])
with top_col2:
    refresh_btn = st.button("↻ Refresh", use_container_width=True)

if st.session_state.status is None or refresh_btn:
    if modules_ok:
        with st.spinner("Loading status..."):
            try:
                st.session_state.status = get_dashboard_status()
                st.session_state.status_error = None
            except Exception as e:
                st.session_state.status_error = str(e)
                st.session_state.status = None

# ── Status cards ──────────────────────────────────────────────────────────────

status = st.session_state.status
err    = st.session_state.status_error

if err:
    st.error(f"Could not load status: {err}")
elif status:
    sq   = status["square"]
    ent  = status["entries"]
    wave = status["wave"]
    loan = status["loan"]

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.subheader("Square")
        if sq["last_payout_date"]:
            days = sq["days_since_payout"]
            st.metric("Last Payout", sq["last_payout_date"],
                      delta=f"−{days}d" if days is not None else "")
            if sq["stale"]:
                st.warning(f"⚠ {days} days since last payout")
            else:
                st.success("✓ Up to date")
        else:
            st.warning("No payouts found")
        st.caption(f"{sq['total_payouts']} total payouts")

    with c2:
        st.subheader("Entries")
        mc1, mc2 = st.columns(2)
        mc1.metric("Unbuilt", ent["unbuilt"])
        mc2.metric("Errors",  ent["errors"])
        if ent["unbuilt"] == 0 and ent["errors"] == 0:
            st.success(f"✓ All built ({ent['posted']} posted)")
        elif ent["errors"] > 0:
            st.error(f"⚠ {ent['errors']} build error(s)")
        else:
            st.warning(f"⚠ {ent['unbuilt']} unbuilt")

    with c3:
        st.subheader("Wave")
        mc3, mc4 = st.columns(2)
        mc3.metric("To Post", wave["staged"])
        mc4.metric("Posted",  wave["posted"])
        if wave["staged"] == 0 and wave["errors"] == 0:
            st.success("✓ All posted to Wave")
        elif wave["errors"] > 0:
            st.error(f"⚠ {wave['errors']} post error(s)")
        else:
            st.warning(f"⚠ {wave['staged']} staged, not posted")

    with c4:
        st.subheader("Loan")
        mc5, mc6 = st.columns(2)
        mc5.metric("Unposted", loan["unposted"])
        mc6.metric("Errors",   loan["errors"])
        if loan["errors"] > 0:
            st.error(f"⚠ {loan['errors']} loan error(s)")
        elif loan["unposted"] == 0:
            st.success("✓ All loan payments posted")
        else:
            st.warning(f"⚠ {loan['unposted']} unposted")

st.divider()

# ── Date range picker ──────────────────────────────────────────────────────────

with st.expander("Square sync date range (default: current year to today)"):
    dr1, dr2 = st.columns(2)
    sync_begin = dr1.date_input("Begin date", value=date(date.today().year, 1, 1))
    sync_end   = dr2.date_input("End date",   value=date.today())

with st.expander("Wave post date (only post entries on or after this date)"):
    wave_post_begin = st.date_input(
        "Post entries from",
        value=date(2025, 1, 1),
        min_value=date(2025, 1, 1),
        help="Cannot go before 2025-01-01 — earlier years are closed books.",
    )

with st.expander("⚠ Close a Year"):
    st.warning(
        "Marking a year closed sets all its journal entries to **closed** status. "
        "They will never be posted to Wave again. Use this after finalizing a year's books."
    )
    close_year_options = list(range(2022, date.today().year + 1))
    close_year_val  = st.selectbox("Year to close", options=close_year_options,
                                    index=None, placeholder="Select year…")
    confirm_close   = st.checkbox("I understand this is permanent and cannot be undone")
    close_yr_btn    = st.button(
        f"Close {close_year_val}" if close_year_val else "Close Year",
        disabled=not (close_year_val and confirm_close),
        type="secondary",
    )

# ── Action buttons ─────────────────────────────────────────────────────────────

st.subheader("Actions")
b1, b2, b3, b4, b5 = st.columns(5)

with b1:
    sq_btn = st.button("Sync Square", use_container_width=True,
                       help="Pull latest Square payouts, entries, payments, and orders into Supabase")
with b2:
    build_btn = st.button("Build Entries", use_container_width=True,
                          help="Compute Wave journal entries from Square data (no API calls to Wave)")
with b3:
    wave_btn = st.button("Post to Wave", use_container_width=True,
                         help="Post staged journal entries to Wave")
with b4:
    loan_btn = st.button("Post Loans", use_container_width=True,
                         help="Build and post staged loan payment entries to Wave")
with b5:
    full_btn = st.button("Full Sync", type="primary", use_container_width=True,
                         help="Run all four steps in sequence")

bx1, bx2 = st.columns([2, 3])
with bx1:
    var_btn = st.button("Check Variances", use_container_width=True,
                        help="Verify payout amounts match entry totals")
with bx2:
    if st.button("Clear Log", use_container_width=True):
        st.session_state.run_log = []
        st.rerun()

# ── Log helper ─────────────────────────────────────────────────────────────────

log_box = st.empty()


def _log(msg: str) -> None:
    st.session_state.run_log.append(msg)
    log_box.code("\n".join(st.session_state.run_log[-60:]), language=None)


def _run(label: str, fn, **kwargs) -> dict:
    _log(f"\n{'─'*50}")
    _log(f"▶ {label}")
    try:
        result = fn(log=_log, **kwargs)
        _log(f"✓ Done — {result}")
        return result
    except Exception as e:
        _log(f"✗ ERROR: {e}")
        st.error(f"{label} failed: {e}")
        return {}


# ── Action handlers ────────────────────────────────────────────────────────────

if not modules_ok:
    st.stop()

ran_any = False

if sq_btn:
    with st.spinner("Syncing Square..."):
        _run("Sync Square", sync_square,
             begin_date=sync_begin.strftime("%Y-%m-%d"),
             end_date=sync_end.strftime("%Y-%m-%d"))
    ran_any = True

if build_btn:
    with st.spinner("Building entries..."):
        _run("Build Wave Entries", build_wave_entries)
    ran_any = True

if wave_btn:
    with st.spinner("Posting to Wave..."):
        _run("Post to Wave", post_to_wave,
             begin_date=wave_post_begin.strftime("%Y-%m-%d"))
    ran_any = True

if loan_btn:
    with st.spinner("Processing loan payments..."):
        _run("Build Loan Entries", build_loan_entries)
        _run("Post Loan Payments", post_loan_payments)
    ran_any = True

if full_btn:
    with st.spinner("Running full sync..."):
        _run("Sync Square", sync_square,
             begin_date=sync_begin.strftime("%Y-%m-%d"),
             end_date=sync_end.strftime("%Y-%m-%d"))
        _run("Build Wave Entries", build_wave_entries)
        _run("Post to Wave", post_to_wave,
             begin_date=wave_post_begin.strftime("%Y-%m-%d"))
        _run("Build Loan Entries", build_loan_entries)
        _run("Post Loan Payments", post_loan_payments)
    ran_any = True

if close_yr_btn and close_year_val and confirm_close:
    with st.spinner(f"Closing year {close_year_val}..."):
        _run(f"Close Year {close_year_val}", close_year, year=int(close_year_val))
    ran_any = True

if var_btn:
    with st.spinner("Checking variances..."):
        try:
            variances = get_variances()
        except Exception as e:
            st.error(f"Variance check failed: {e}")
            variances = None

    if variances is not None:
        if variances:
            st.warning(f"{len(variances)} payout(s) with variance > 5 cents")
            st.table([{
                "Payout ID":    v["payout_id"][:22],
                "Date":         v["arrival_date"],
                "Payout $":     f"{v['payout_cents'] / 100:.2f}",
                "Entries $":    f"{v['entries_cents'] / 100:.2f}",
                "Variance ¢":   v["variance_cents"],
            } for v in variances])
        else:
            st.success("All payouts balance perfectly — no variances found.")

# Force status refresh after any action
if ran_any:
    st.session_state.status = None

# ── Run log display ────────────────────────────────────────────────────────────

if st.session_state.run_log:
    st.divider()
    st.subheader("Run Log")
    st.code("\n".join(st.session_state.run_log[-100:]), language=None)

# ── Sync history ──────────────────────────────────────────────────────────────

if status and status.get("sync_log"):
    st.divider()
    st.subheader("Recent Sync History")
    history_rows = []
    for row in status["sync_log"]:
        ts = (row.get("synced_at") or "")[:19].replace("T", " ")
        history_rows.append({
            "Time":     ts,
            "Range":    row.get("date_range", ""),
            "Payouts":  row.get("payouts_found", 0),
            "Entries":  row.get("entries_found", 0),
            "Payments": row.get("payments_found", 0),
            "Orders":   row.get("orders_found", 0),
        })
    st.dataframe(history_rows, use_container_width=True, hide_index=True)
