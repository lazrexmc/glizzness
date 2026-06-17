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
    from db import get_dashboard_status, get_variances, get_financials
    from sync import (
        sync_square, build_wave_entries, post_to_wave,
        post_single_loan_payment, close_year, import_wave_csv,
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
if "loan_form_open" not in st.session_state:
    st.session_state.loan_form_open = False
if "financials" not in st.session_state:
    st.session_state.financials = None

# ── Load / refresh status ─────────────────────────────────────────────────────

top_col1, top_col2 = st.columns([6, 1])
with top_col2:
    refresh_btn = st.button("↻ Refresh", width='stretch')

if st.session_state.status is None or refresh_btn:
    if modules_ok:
        with st.spinner("Loading status..."):
            try:
                st.session_state.status     = get_dashboard_status()
                st.session_state.financials = get_financials()
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

with st.expander("Import Wave Transactions CSV"):
    st.caption(
        "Wave → Accounting → Transactions → Export → Transactions CSV  "
        "— upload here to keep the wave_transactions table in sync."
    )
    wave_csv_file   = st.file_uploader("Wave CSV", type=["csv"], label_visibility="collapsed")
    wave_csv_replace = st.checkbox(
        "Replace existing rows for this file (use after correcting entries in Wave)",
        key="wave_csv_replace",
    )
    wave_import_btn = st.button(
        "Import to Supabase",
        disabled=wave_csv_file is None,
        type="primary",
        key="wave_import_btn",
    )

# ── Action buttons ─────────────────────────────────────────────────────────────

st.subheader("Actions")
b1, b2, b3, b4, b5 = st.columns(5)

with b1:
    sq_btn = st.button("Sync Square", width='stretch',
                       help="Pull latest Square payouts, entries, payments, and orders into Supabase")
with b2:
    build_btn = st.button("Build Entries", width='stretch',
                          help="Compute Wave journal entries from Square data (no API calls to Wave)")
with b3:
    wave_btn = st.button("Post to Wave", width='stretch',
                         help="Post staged journal entries to Wave")
with b4:
    loan_btn = st.button("Log Loan", width='stretch',
                         help="Enter a loan payment from your bank statement and post to Wave")
with b5:
    full_btn = st.button("Full Sync", type="primary", width='stretch',
                         help="Run all four steps in sequence")

bx1, bx2 = st.columns([2, 3])
with bx1:
    var_btn = st.button("Check Variances", width='stretch',
                        help="Verify payout amounts match entry totals")
with bx2:
    if st.button("Clear Log", width='stretch'):
        st.session_state.run_log = []
        st.rerun()

# ── Loan payment entry form ────────────────────────────────────────────────────
# Rendered here so it appears above the log; handlers are below after _run().

loan_form_visible  = st.session_state.loan_form_open
send_loan_btn      = False
cancel_loan_btn    = False
loan_date_val      = date.today()
loan_principal_val = 0.0
loan_interest_val  = 0.0
loan_total_val     = 0.0

if loan_form_visible:
    with st.container(border=True):
        st.subheader("Log Loan Payment")
        lf1, lf2, lf3 = st.columns(3)
        loan_date_val      = lf1.date_input("Payment date", value=date.today(), key="lf_date")
        loan_principal_val = lf2.number_input("Principal ($)", min_value=0.0, step=0.01,
                                               format="%.2f", key="lf_principal")
        loan_interest_val  = lf3.number_input("Interest ($)", min_value=0.0, step=0.01,
                                               format="%.2f", key="lf_interest")
        loan_total_val = round(float(loan_principal_val) + float(loan_interest_val), 2)
        if loan_total_val > 0:
            st.caption(f"Total: **${loan_total_val:.2f}**")
        lfa, lfb = st.columns([1, 5])
        send_loan_btn   = lfa.button("Send to Wave", type="primary",
                                      disabled=(loan_total_val <= 0), key="lf_send")
        cancel_loan_btn = lfb.button("Cancel", key="lf_cancel")

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
    st.session_state.loan_form_open = True
    st.rerun()

if loan_form_visible and cancel_loan_btn:
    st.session_state.loan_form_open = False
    st.rerun()

if loan_form_visible and send_loan_btn and loan_total_val > 0:
    with st.spinner("Posting loan payment to Wave..."):
        _run("Post Loan Payment", post_single_loan_payment,
             payment_date=loan_date_val.strftime("%Y-%m-%d"),
             principal=float(loan_principal_val),
             interest=float(loan_interest_val))
    st.session_state.loan_form_open = False
    st.session_state.status = None
    st.rerun()

if full_btn:
    with st.spinner("Running full sync..."):
        _run("Sync Square", sync_square,
             begin_date=sync_begin.strftime("%Y-%m-%d"),
             end_date=sync_end.strftime("%Y-%m-%d"))
        _run("Build Wave Entries", build_wave_entries)
        _run("Post to Wave", post_to_wave,
             begin_date=wave_post_begin.strftime("%Y-%m-%d"))
    ran_any = True

if wave_import_btn and wave_csv_file is not None:
    with st.spinner(f"Importing {wave_csv_file.name}..."):
        content = wave_csv_file.read().decode("utf-8-sig")
        _run("Import Wave CSV", import_wave_csv,
             file_content=content,
             source_name=wave_csv_file.name,
             replace=wave_csv_replace)
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

# Force status + financials refresh after any action
if ran_any:
    st.session_state.status     = None
    st.session_state.financials = None

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
    st.dataframe(history_rows, width='stretch', hide_index=True)

# ── Financial Reports ──────────────────────────────────────────────────────────

st.divider()
with st.expander("📊 Financial Reports"):
    fin = st.session_state.financials
    if fin is None:
        st.info("Click ↻ Refresh to load reports.")
    else:
        import pandas as pd

        by_year  = fin["by_year"]
        by_month = fin["by_month"]
        curr_yr  = str(date.today().year)

        if not by_year:
            st.info("No posted entries found — sync and post Square data first.")
        else:
            # ── Annual P&L ────────────────────────────────────────────────────
            st.subheader("Annual Summary")

            def _d(c):  return f"${c/100:,.0f}"
            def _neg(c): return f"(${c/100:,.0f})" if c else "—"

            tbl = {}
            for yr in sorted(by_year.keys()):
                b   = by_year[yr]
                gs  = b["gross_sales_cents"]
                dis = b["discounts_cents"]
                ret = b["returns_cents"]
                lbl = f"{yr} YTD" if yr == curr_yr else yr
                tbl[lbl] = {
                    "Gross Sales":          _d(gs),
                    "Discounts":            _neg(dis),
                    "Returns":              _neg(ret),
                    "Net Sales":            _d(gs - dis - ret),
                    "Sales Tax Collected":  _d(b["taxes_cents"]),
                    "Tips Collected":       _d(b["tips_cents"]),
                    "Processing Fees":      _neg(b["fees_cents"]),
                    "Net to Bank":          _d(b["payout_net_cents"]),
                    "# Payouts":            str(b["count"]),
                }

            st.dataframe(pd.DataFrame(tbl), width='stretch')
            st.caption(
                "Sales Tax Collected is a pass-through liability remitted to the state — "
                "not business income or expense."
            )

            # ── Monthly revenue chart ─────────────────────────────────────────
            st.subheader(f"{curr_yr} Monthly Revenue")
            MO = {"01":"Jan","02":"Feb","03":"Mar","04":"Apr","05":"May","06":"Jun",
                  "07":"Jul","08":"Aug","09":"Sep","10":"Oct","11":"Nov","12":"Dec"}
            curr_months = {k: v for k, v in by_month.items() if k[:4] == curr_yr}
            if curr_months:
                chart_df = pd.DataFrame({
                    "Gross Sales ($)": {
                        MO.get(k[5:], k[5:]): curr_months[k]["gross_sales_cents"] / 100
                        for k in sorted(curr_months)
                    }
                })
                st.bar_chart(chart_df)
            else:
                st.info(f"No {curr_yr} data yet.")

            # ── Key metrics ───────────────────────────────────────────────────
            st.subheader(f"{curr_yr} at a Glance")
            cy = by_year.get(curr_yr, {})
            if cy:
                n_mo       = max(len(curr_months), 1)
                avg_mo     = (cy["gross_sales_cents"] / 100) / n_mo
                annualized = avg_mo * 12
                tip_rate   = cy["tips_cents"] / max(cy["gross_sales_cents"], 1) * 100
                fee_rate   = cy["fees_cents"] / max(cy["gross_sales_cents"], 1) * 100

                km1, km2, km3, km4 = st.columns(4)
                km1.metric("Avg Monthly Revenue", f"${avg_mo:,.0f}")
                km2.metric("Annualized Revenue",  f"${annualized:,.0f}")
                km3.metric("Tip Rate",             f"{tip_rate:.1f}%")
                km4.metric("Processing Fee Rate",  f"{fee_rate:.1f}%")
