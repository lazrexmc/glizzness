#!/usr/bin/env python3
"""
valuation.py --Business valuation report for The Glizzness LLC.

Pulls data from glizzness.db and produces a multi-method valuation.
Square data is used for revenue (2025-2026, more accurate).
Wave CSV data is used for expenses, balance sheet, and 2023-2024 revenue.

Usage:
  python valuation.py             # full report, all years
  python valuation.py --detail    # include per-account expense lines
  python valuation.py --year 2025 # focus on a single year
"""

import sys
import sqlite3
from datetime import date

DB_PATH = "glizzness.db"

# ── Formatting helpers ────────────────────────────────────────────────────────

def d(n, w=12):
    """Format a dollar amount, right-justified."""
    return f"${n:>{w-1},.2f}"

def pct(n, d):
    if d == 0:
        return "   n/a"
    return f"{n/d*100:>5.1f}%"

def hr(char="-", width=72):
    print(char * width)

def section(title):
    print()
    hr("=")
    print(f"  {title}")
    hr("=")


# ── Data queries ──────────────────────────────────────────────────────────────

def get_square_by_year(conn):
    """Square revenue from journal_entries (2025-2026, posted payouts only)."""
    rows = conn.execute("""
        SELECT substr(arrival_date,1,4) yr,
               COUNT(*)                              payouts,
               SUM(gross_sales_cents) / 100.0        gross,
               SUM(tips_cents)        / 100.0        tips,
               SUM(taxes_cents)       / 100.0        taxes,
               SUM(fees_cents)        / 100.0        fees,
               SUM(payout_net_cents)  / 100.0        net
        FROM journal_entries
        WHERE status = 'posted'
        GROUP BY yr
        ORDER BY yr
    """).fetchall()
    return {r[0]: dict(zip(
        ("payouts", "gross", "tips", "taxes", "fees", "net"), r[1:]
    )) for r in rows}


def get_wave_income_by_year(conn):
    """Wave income accounts by year --used for 2023-2024 and for cross-check."""
    rows = conn.execute("""
        SELECT substr(txn_date,1,4) yr, account_name,
               SUM(credit) cr, SUM(debit) dr
        FROM wave_transactions
        WHERE account_name IN (
            'Food & Beverage Sales',
            'Uncategorized Income',
            'Insurance Proceeds'
        )
        GROUP BY yr, account_name
        ORDER BY yr, account_name
    """).fetchall()
    out = {}
    for yr, acct, cr, dr in rows:
        out.setdefault(yr, {})[acct] = (cr or 0, dr or 0)
    return out


def get_cogs_by_year(conn):
    """COGS accounts from Wave by year."""
    rows = conn.execute("""
        SELECT substr(txn_date,1,4) yr, account_name,
               SUM(debit) dr, SUM(credit) cr
        FROM wave_transactions wt
        JOIN wave_accounts wa ON wt.account_name = wa.name
        WHERE wa.subtype_value = 'COST_OF_GOODS_SOLD'
        GROUP BY yr, account_name
        ORDER BY yr, SUM(debit) DESC
    """).fetchall()
    out = {}
    for yr, acct, dr, cr in rows:
        out.setdefault(yr, {})[acct] = (dr or 0) - (cr or 0)
    return out


def get_opex_by_year(conn):
    """Operating expense accounts from Wave by year (excludes COGS)."""
    rows = conn.execute("""
        SELECT substr(txn_date,1,4) yr,
               wa.subtype_value subtype,
               wt.account_name,
               SUM(wt.debit)  dr,
               SUM(wt.credit) cr
        FROM wave_transactions wt
        JOIN wave_accounts wa ON wt.account_name = wa.name
        WHERE wa.type_value  = 'EXPENSE'
          AND wa.subtype_value NOT IN ('COST_OF_GOODS_SOLD', 'UNCATEGORIZED_EXPENSE')
        GROUP BY yr, wa.subtype_value, wt.account_name
        ORDER BY yr, SUM(wt.debit) DESC
    """).fetchall()
    out = {}
    for yr, subtype, acct, dr, cr in rows:
        out.setdefault(yr, {}).setdefault(acct, {})
        out[yr][acct] = (dr or 0) - (cr or 0)
    return out


def get_uncat_expense_by_year(conn):
    rows = conn.execute("""
        SELECT substr(txn_date,1,4) yr, SUM(debit) dr
        FROM wave_transactions
        WHERE account_name = 'Uncategorized Expense'
        GROUP BY yr ORDER BY yr
    """).fetchall()
    return {r[0]: r[1] or 0 for r in rows}


def get_owner_equity_by_year(conn):
    """Owner draws and investments from Wave equity accounts."""
    rows = conn.execute("""
        SELECT substr(txn_date,1,4) yr, account_name,
               SUM(debit) dr, SUM(credit) cr
        FROM wave_transactions
        WHERE account_name IN (
            'Owner Investment / Drawings',
            'Cash Deposit by Owner'
        )
        GROUP BY yr, account_name
        ORDER BY yr
    """).fetchall()
    out = {}
    for yr, acct, dr, cr in rows:
        out.setdefault(yr, {})
        out[yr][acct] = {'dr': dr or 0, 'cr': cr or 0}
    return out


def get_interest_by_year(conn):
    """Interest expense from loan_payments (more accurate than Wave)."""
    rows = conn.execute("""
        SELECT substr(payment_date,1,4) yr, SUM(interest) interest
        FROM loan_payments GROUP BY yr ORDER BY yr
    """).fetchall()
    return {r[0]: r[1] or 0 for r in rows}


def get_depreciation_by_year(conn):
    rows = conn.execute("""
        SELECT substr(txn_date,1,4) yr, SUM(debit) dr
        FROM wave_transactions
        WHERE account_name = 'Depreciation Expense'
        GROUP BY yr ORDER BY yr
    """).fetchall()
    return {r[0]: r[1] or 0 for r in rows}


def get_balance_sheet(conn):
    """Simplified balance sheet from Wave account totals."""
    rows = conn.execute("""
        SELECT wa.type_value, wa.subtype_value, wt.account_name,
               SUM(wt.debit) total_dr, SUM(wt.credit) total_cr
        FROM wave_transactions wt
        JOIN wave_accounts wa ON wt.account_name = wa.name
        GROUP BY wa.type_value, wa.subtype_value, wt.account_name
        ORDER BY wa.type_value, wa.subtype_value
    """).fetchall()

    assets = liabilities = equity = 0.0
    equipment_gross = equipment_depreciation = 0.0
    loan_balance = 0.0
    detail = {}

    for type_val, subtype, acct, dr, cr in rows:
        dr = dr or 0
        cr = cr or 0
        net_dr = dr - cr   # positive = DR balance (normal for assets)
        net_cr = cr - dr   # positive = CR balance (normal for liabilities/equity)

        detail.setdefault(type_val, {})[acct] = {
            'subtype': subtype, 'dr': dr, 'cr': cr, 'net_dr': net_dr
        }

        if type_val == 'ASSET':
            if subtype == 'PROPERTY_PLANT_EQUIPMENT':
                equipment_gross += net_dr
            elif subtype == 'DEPRECIATION_AND_AMORTIZATION':
                equipment_depreciation += net_cr   # accumulated depreciation = CR balance
            elif subtype not in ('TRANSFERS', 'MONEY_IN_TRANSIT', 'OTHER_CURRENT_ASSETS'):
                assets += net_dr
        elif type_val == 'LIABILITY':
            if subtype == 'LOANS':
                loan_balance = net_cr
            liabilities += net_cr
        elif type_val == 'EQUITY':
            equity += net_cr

    return {
        'assets': assets,
        'equipment_gross': equipment_gross,
        'equipment_depreciation': equipment_depreciation,
        'liabilities': liabilities,
        'loan_balance': loan_balance,
        'equity': equity,
        'detail': detail,
    }


def get_current_loan_balance(conn):
    row = conn.execute(
        "SELECT balance FROM loan_payments ORDER BY payment_date DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else 0.0


def get_data_quality(conn):
    """Flags for incomplete / uncategorized data."""
    flags = []

    # Uncategorized income by year
    rows = conn.execute("""
        SELECT substr(txn_date,1,4), SUM(credit)
        FROM wave_transactions WHERE account_name='Uncategorized Income'
        GROUP BY 1 ORDER BY 1
    """).fetchall()
    for yr, amt in rows:
        if (amt or 0) > 100:
            flags.append(f"  {yr}: Uncategorized Income ${amt:,.2f} -- re-export CSV after "
                          "categorizing bank imports to apply corrections")

    # Uncategorized expenses
    rows = conn.execute("""
        SELECT substr(txn_date,1,4), SUM(debit)
        FROM wave_transactions WHERE account_name='Uncategorized Expense'
        GROUP BY 1 ORDER BY 1
    """).fetchall()
    for yr, amt in rows:
        if (amt or 0) > 100:
            flags.append(f"  {yr}: Uncategorized Expense ${amt:,.2f} -- review and categorize in Wave")

    # Years with Square data
    sq_years = conn.execute(
        "SELECT DISTINCT substr(arrival_date,1,4) FROM journal_entries WHERE status='posted'"
    ).fetchall()
    sq_year_set = {r[0] for r in sq_years}

    wave_years = conn.execute(
        "SELECT DISTINCT substr(txn_date,1,4) FROM wave_transactions"
    ).fetchall()
    for (yr,) in wave_years:
        if yr not in sq_year_set:
            flags.append(f"  {yr}: No Square data -- revenue pulled from Wave CSV only")

    return flags


# ── Report sections ───────────────────────────────────────────────────────────

def report_revenue(sq, wv, years, focus_year=None):
    section("REVENUE")
    if focus_year:
        years = [focus_year]

    header = f"  {'Source':<28}" + "".join(f"{yr:>12}" for yr in years)
    print(header)
    hr()

    # Square gross sales (where available)
    row = f"  {'Square Gross Sales':<28}"
    for yr in years:
        v = sq.get(yr, {}).get('gross', 0)
        row += f"{d(v):>12}" if v else f"{'--':>12}"
    print(row)

    row = f"  {'  Tips':<28}"
    for yr in years:
        v = sq.get(yr, {}).get('tips', 0)
        row += f"{d(v):>12}" if v else f"{'--':>12}"
    print(row)

    row = f"  {'  Sales Tax Collected':<28}"
    for yr in years:
        v = sq.get(yr, {}).get('taxes', 0)
        row += f"{d(v):>12}" if v else f"{'--':>12}"
    print(row)

    # Wave Food & Bev (for years without Square, or as cross-check)
    print()
    row = f"  {'Wave Food & Bev Sales':<28}"
    for yr in years:
        v = (wv.get(yr, {}).get('Food & Beverage Sales') or (0, 0))[0]
        row += f"{d(v):>12}" if v else f"{'--':>12}"
    print(row)

    row = f"  {'Wave Uncategorized Income':<28}"
    for yr in years:
        v = (wv.get(yr, {}).get('Uncategorized Income') or (0, 0))[0]
        row += f"{d(v):>12}" if v else f"{'--':>12}"
    print(row)

    # Best-estimate revenue (Square where available, else Wave Food & Bev)
    print()
    hr()
    row = f"  {'REVENUE (best estimate)':<28}"
    for yr in years:
        if yr in sq:
            v = sq[yr]['gross']
        else:
            v = (wv.get(yr, {}).get('Food & Beverage Sales') or (0, 0))[0]
        row += f"{d(v):>12}"
    print(row)
    hr()
    print(f"  * Square data (2025-2026) is post-automation and more accurate.")
    print(f"  * 2023-2024 revenue is from Wave CSV; may exclude cash/unreported sales.")


def report_pl(sq, wv, cogs_by_yr, opex_by_yr, uncat_by_yr, interest_by_yr, depr_by_yr,
              equity_by_yr, years, detail=False, focus_year=None):
    if focus_year:
        years = [focus_year]

    section("PROFIT & LOSS SUMMARY")
    hdr = f"  {'':30}" + "".join(f"{yr:>12}" for yr in years)
    print(hdr)
    hr()

    # Revenue
    rev = {}
    for yr in years:
        if yr in sq:
            rev[yr] = sq[yr]['gross']
        else:
            rev[yr] = (wv.get(yr, {}).get('Food & Beverage Sales') or (0, 0))[0]

    row = f"  {'Revenue':<30}" + "".join(f"{d(rev.get(yr,0)):>12}" for yr in years)
    print(row)

    # COGS
    total_cogs = {}
    for yr in years:
        total_cogs[yr] = sum(cogs_by_yr.get(yr, {}).values())
    row = f"  {'COGS':<30}" + "".join(f"{d(-total_cogs.get(yr,0)):>12}" for yr in years)
    print(row)

    if detail:
        for acct in sorted({a for yr_d in cogs_by_yr.values() for a in yr_d}):
            row = f"  {'  ' + acct:<30}" + "".join(
                f"{d(-cogs_by_yr.get(yr,{}).get(acct,0)):>12}" for yr in years)
            print(row)

    # Gross Profit
    gp = {yr: rev.get(yr, 0) - total_cogs.get(yr, 0) for yr in years}
    hr()
    row = f"  {'Gross Profit':<30}" + "".join(f"{d(gp.get(yr,0)):>12}" for yr in years)
    print(row)
    row = f"  {'  Gross Margin':<30}" + "".join(
        f"{pct(gp.get(yr,0), rev.get(yr,1)):>12}" for yr in years)
    print(row)
    print()

    # Operating Expenses
    all_opex_accts = sorted({a for yr_d in opex_by_yr.values() for a in yr_d},
                             key=lambda a: -max(opex_by_yr.get(yr, {}).get(a, 0) for yr in years))
    total_opex = {}
    for yr in years:
        total_opex[yr] = sum(opex_by_yr.get(yr, {}).values()) + uncat_by_yr.get(yr, 0)

    row = f"  {'Operating Expenses':<30}" + "".join(f"{d(-total_opex.get(yr,0)):>12}" for yr in years)
    print(row)

    if detail:
        for acct in all_opex_accts:
            any_val = any(opex_by_yr.get(yr, {}).get(acct, 0) for yr in years)
            if not any_val:
                continue
            row = f"  {'  ' + acct[:27]:<30}" + "".join(
                f"{d(-opex_by_yr.get(yr,{}).get(acct,0)):>12}" for yr in years)
            print(row)
        uncat = {yr: uncat_by_yr.get(yr, 0) for yr in years}
        if any(uncat.values()):
            row = f"  {'  Uncategorized Expense':<30}" + "".join(
                f"{d(-uncat.get(yr,0)):>12}" for yr in years)
            print(row)

    # EBITDA
    ebitda = {yr: gp.get(yr, 0) - total_opex.get(yr, 0) for yr in years}
    hr()
    row = f"  {'EBITDA (approx)':<30}" + "".join(f"{d(ebitda.get(yr,0)):>12}" for yr in years)
    print(row)
    row = f"  {'  EBITDA Margin':<30}" + "".join(
        f"{pct(ebitda.get(yr,0), rev.get(yr,1)):>12}" for yr in years)
    print(row)

    print()
    print("  Add-backs to EBITDA (for SDE calculation):")

    # Interest
    row = f"  {'  + Interest Expense':<30}" + "".join(
        f"{d(interest_by_yr.get(yr,0)):>12}" for yr in years)
    print(row)

    # Depreciation
    row = f"  {'  + Depreciation':<30}" + "".join(
        f"{d(depr_by_yr.get(yr,0)):>12}" for yr in years)
    print(row)

    # Owner draws (net)
    net_draws = {}
    for yr in years:
        eq = equity_by_yr.get(yr, {})
        draws_dr = eq.get('Owner Investment / Drawings', {}).get('dr', 0)
        draws_cr = eq.get('Owner Investment / Drawings', {}).get('cr', 0)
        inv_cr   = eq.get('Cash Deposit by Owner', {}).get('cr', 0)
        inv_dr   = eq.get('Cash Deposit by Owner', {}).get('dr', 0)
        net_draws[yr] = (draws_dr - draws_cr) + (inv_dr - inv_cr)
    row = f"  {'  + Owner Draws (net)':<30}" + "".join(
        f"{d(max(0, net_draws.get(yr,0))):>12}" for yr in years)
    print(row)

    # SDE
    sde = {yr: ebitda.get(yr, 0)
                + interest_by_yr.get(yr, 0)
                + depr_by_yr.get(yr, 0)
                + max(0, net_draws.get(yr, 0))
           for yr in years}
    hr()
    row = f"  {'SDE (Seller\'s Disc. Earnings)':<30}" + "".join(f"{d(sde.get(yr,0)):>12}" for yr in years)
    print(row)

    return sde, rev


def report_balance_sheet(bs, loan_actual):
    section("BALANCE SHEET  (from Wave CSV -- point-in-time)")
    hr()

    equipment_net = bs['equipment_gross'] - bs['equipment_depreciation']

    print(f"  ASSETS")
    print(f"  {'  Cash & Bank (Checking 529 net)':<40} {d(bs['assets']):>12}")
    print(f"  {'  Equipment (gross book value)':<40} {d(bs['equipment_gross']):>12}")
    print(f"  {'  Less: Accumulated Depreciation':<40} {d(-bs['equipment_depreciation']):>12}")
    print(f"  {'  Equipment (net book value)':<40} {d(equipment_net):>12}")
    total_assets = bs['assets'] + equipment_net
    hr()
    print(f"  {'  TOTAL ASSETS':<40} {d(total_assets):>12}")

    print()
    print(f"  LIABILITIES")
    print(f"  {'  Weenie Wagon Loan (current)':<40} {d(loan_actual):>12}")
    other_liab = bs['liabilities'] - bs['loan_balance']
    if abs(other_liab) > 1:
        print(f"  {'  Sales Tax & Other Payables':<40} {d(other_liab):>12}")
    total_liab = loan_actual + max(0, other_liab)
    hr()
    print(f"  {'  TOTAL LIABILITIES':<40} {d(total_liab):>12}")

    print()
    net_book = total_assets - total_liab
    hr("=")
    print(f"  {'NET BOOK VALUE (Assets - Liabilities)':<40} {d(net_book):>12}")
    hr("=")
    print()
    print("  Note: Equipment at book value. Fair market value may differ.")
    print("  Note: Wave CSV data may lag actual Wave balances; re-export for precision.")

    return total_assets, total_liab, net_book, equipment_net


def report_valuation(sde, rev, years, total_assets, total_liab, net_book, equipment_net, loan_actual):
    section("VALUATION  (three methods)")

    today      = date.today()
    current_yr = str(today.year)

    # Primary basis: most recent full year
    full_years = [yr for yr in years if int(yr) < today.year]
    val_year   = full_years[-1] if full_years else years[-1]
    sde_val    = sde.get(val_year, 0)
    rev_val    = rev.get(val_year, 0)

    # Current-year trend annualization (if partial-year data exists)
    has_trend   = current_yr in sde and current_yr != val_year
    sde_trend   = rev_trend = 0.0
    elapsed_days = ann_factor = 0
    if has_trend:
        elapsed_days = (today - date(today.year, 1, 1)).days + 1
        ann_factor   = 365 / elapsed_days
        sde_trend    = sde.get(current_yr, 0) * ann_factor
        rev_trend    = rev.get(current_yr, 0) * ann_factor

    print(f"\n  Basis year: {val_year}  (most recent full year)")
    print(f"  SDE  {val_year}:     {d(sde_val)}")
    print(f"  Revenue {val_year}: {d(rev_val)}")
    if has_trend:
        print(f"\n  {current_yr} YTD ({elapsed_days} days, annualized x{ann_factor:.2f}):")
        print(f"  SDE  {current_yr} annualized:    {d(sde_trend)}")
        print(f"  Revenue {current_yr} annualized: {d(rev_trend)}")
    print()

    floor = equipment_net - loan_actual

    # ── Method 1: SDE Multiple ────────────────────────────────────────────────
    hr("-")
    print("  METHOD 1 -- SDE Multiple  (most common for owner-operated businesses)")
    hr("-")
    print("  Food truck SDE multiples typically range 1.5x - 2.5x.")
    print("  Lower end: owner-dependent, single truck.")
    print("  Upper end: established brand, strong repeat customer base, documented systems.")
    print()
    if sde_val > 0:
        print(f"  Basis ({val_year}):")
        for m in (1.5, 2.0, 2.5):
            print(f"  {m:.1f}x  SDE:  {d(sde_val)}  =  {d(sde_val * m, 14)}")
    else:
        print(f"  [!] {val_year} SDE is negative -- SDE multiple does not apply for basis year.")
    if has_trend and sde_trend > 0:
        print(f"\n  Trend ({current_yr} annualized):")
        for m in (1.5, 2.0, 2.5):
            print(f"  {m:.1f}x  SDE:  {d(sde_trend)}  =  {d(sde_trend * m, 14)}")

    # ── Method 2: Revenue Multiple ────────────────────────────────────────────
    print()
    hr("-")
    print("  METHOD 2 -- Revenue Multiple  (quick sanity check)")
    hr("-")
    print("  Food service revenue multiples typically 0.25x - 0.45x.")
    print()
    print(f"  Basis ({val_year}):")
    for m in (0.25, 0.35, 0.45):
        print(f"  {m:.2f}x  Revenue:  {d(rev_val)}  =  {d(rev_val * m, 14)}")
    if has_trend:
        print(f"\n  Trend ({current_yr} annualized):")
        for m in (0.25, 0.35, 0.45):
            print(f"  {m:.2f}x  Revenue:  {d(rev_trend)}  =  {d(rev_trend * m, 14)}")

    # ── Method 3: Asset-Based ─────────────────────────────────────────────────
    print()
    hr("-")
    print("  METHOD 3 -- Asset-Based  (floor / liquidation value)")
    hr("-")
    print(f"  Equipment net book value:  {d(equipment_net, 14)}")
    print(f"  Less: Loan balance:       {d(-loan_actual, 14)}")
    print(f"  Net tangible value:        {d(floor, 14)}")
    print()
    print("  Book value shown; consult equipment appraiser for fair market value.")
    print()

    # ── Summary Range ─────────────────────────────────────────────────────────
    hr("=")
    print("  VALUATION RANGE SUMMARY")
    hr("=")

    def _range(sde_n, rev_n, label):
        lo = min(
            sde_n * 1.5 if sde_n > 0 else float('inf'),
            rev_n * 0.25,
            floor,
        )
        hi  = max(sde_n * 2.5 if sde_n > 0 else 0, rev_n * 0.45, floor)
        mid = (lo + hi) / 2
        print(f"  {label}:")
        if lo < float('inf') and lo > 0:
            print(f"  Low  (asset floor / 0.25x rev):  {d(lo, 14)}")
            print(f"  Mid  (2.0x SDE / 0.35x rev):     {d(mid, 14)}")
            print(f"  High (2.5x SDE / 0.45x rev):     {d(hi, 14)}")
        else:
            print(f"  Low  (0.25x revenue):  {d(rev_n * 0.25, 14)}")
            print(f"  Mid  (0.35x revenue):  {d(rev_n * 0.35, 14)}")
            print(f"  High (asset floor):    {d(floor, 14)}")

    _range(sde_val, rev_val, f"{val_year} actual")
    if has_trend:
        print()
        _range(sde_trend, rev_trend, f"{current_yr} annualized trend")
        print()
        print("  Trend values are projections based on YTD performance.")
        print("  Actual annual results may vary with seasonality.")
    hr("=")


def report_data_quality(flags):
    section("DATA COMPLETENESS & CAVEATS")
    if flags:
        for f in flags:
            print(f)
    else:
        print("  No data quality issues detected.")
    print()
    print("  General notes:")
    print("  * 2023-2024 revenue is from Wave CSV only; may exclude unreported cash sales.")
    print("  * Owner meals or personal expenses run through the business understate margins.")
    print("  * Equipment FMV should be assessed by an appraiser, not book value.")
    print("  * Intangibles (brand, location rights, customer loyalty) not captured here.")
    print("  * Re-export Wave CSVs after any corrections and run --replace to refresh.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args      = sys.argv[1:]
    detail    = "--detail" in args
    focus_yr  = None
    for a in args:
        if a.isdigit() and len(a) == 4:
            focus_yr = a

    conn = sqlite3.connect(DB_PATH)

    sq          = get_square_by_year(conn)
    wv          = get_wave_income_by_year(conn)
    cogs_by_yr  = get_cogs_by_year(conn)
    opex_by_yr  = get_opex_by_year(conn)
    uncat_by_yr = get_uncat_expense_by_year(conn)
    interest_yr = get_interest_by_year(conn)
    depr_yr     = get_depreciation_by_year(conn)
    equity_yr   = get_owner_equity_by_year(conn)
    bs          = get_balance_sheet(conn)
    loan_actual = get_current_loan_balance(conn)
    flags       = get_data_quality(conn)

    # All years with any data
    all_years = sorted(set(
        list(sq.keys()) + list(wv.keys()) + list(cogs_by_yr.keys()) + list(opex_by_yr.keys())
    ))

    conn.close()

    print()
    hr("=", 72)
    print("  THE GLIZZNESS LLC -- Business Valuation Report")
    print(f"  Generated: {date.today()}")
    hr("=", 72)

    report_revenue(sq, wv, all_years, focus_yr)
    sde, rev = report_pl(sq, wv, cogs_by_yr, opex_by_yr, uncat_by_yr,
                          interest_yr, depr_yr, equity_yr,
                          all_years, detail=detail, focus_year=focus_yr)
    ta, tl, nb, equip_net = report_balance_sheet(bs, loan_actual)
    report_valuation(sde, rev, all_years, ta, tl, nb, equip_net, loan_actual)
    report_data_quality(flags)


if __name__ == "__main__":
    main()
