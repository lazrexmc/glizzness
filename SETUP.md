# Glizzness Square → Wave Reconciliation — Setup Guide

## Step 1: Install Python dependencies

```powershell
pip install requests
```

## Step 2: Set environment variables

Open PowerShell and run (paste your actual tokens):

```powershell
$env:SQUARE_TOKEN     = "your_square_production_access_token"
$env:WAVE_TOKEN       = "your_wave_api_token"
$env:WAVE_BUSINESS_ID = "your_wave_business_id"
```

**Square token**: Square Developer Dashboard → your app → Production → Access Token
**Wave token**: Wave → Settings → Developer → Manage API tokens
**Wave Business ID**: Wave → Settings → Business — copy the ID from the URL

## Step 3: Find your Wave account IDs

```powershell
python reconcile.py --list-accounts
```

This prints all accounts in your Wave chart of accounts.
Find these 7 accounts and note their IDs:

| Env Var                      | Account to find in Wave                      |
|------------------------------|----------------------------------------------|
| WAVE_CLEARING_ACCOUNT_ID     | Square Settlements Clearing (Other ST Asset) |
| WAVE_BANK_ACCOUNT_ID         | Checking account (Square deposit bank)       |
| WAVE_SALES_REVENUE_ID        | Sales (Income)                               |
| WAVE_TIPS_INCOME_ID          | Tips Income (create if missing)              |
| WAVE_PROCESSING_FEES_ID      | Payment Processing Fees (Expense)            |
| WAVE_SALES_TAX_ID            | Sales Tax (Liability / Tax Payable)          |
| WAVE_SALES_RETURNS_ID        | Sales Returns & Allowances (create if missing) |
| WAVE_DISCOUNTS_ID            | Sales Discounts & Comps (create if missing)  |

Set them in PowerShell:
```powershell
$env:WAVE_CLEARING_ACCOUNT_ID = "QWNjb3VudDoyNTUxMzY3NzMwMTA4MzQ1MjgzO0J1c2luZXNzOmJhMmQwOGFkLTNhNzUtNDkxOC1iZDljLTc4MWFlZmFkMzczNg=="
$env:WAVE_BANK_ACCOUNT_ID     = "QWNjb3VudDo..."
$env:WAVE_SALES_REVENUE_ID    = "QWNjb3VudDo..."
$env:WAVE_TIPS_INCOME_ID      = "QWNjb3VudDo..."
$env:WAVE_PROCESSING_FEES_ID  = "QWNjb3VudDo..."
$env:WAVE_SALES_TAX_ID        = "QWNjb3VudDo..."
$env:WAVE_SALES_RETURNS_ID    = "QWNjb3VudDo..."
$env:WAVE_DISCOUNTS_ID        = "QWNjb3VudDo..."
```

## Step 4: Test with one day

```powershell
python reconcile.py 2025-10-22
```

Check Wave to confirm the journal entry was created correctly before running the backfill.

## Step 5: Backfill all of 2025

```powershell
python reconcile.py 2025-01-01 2025-12-31
```

The script is safe to re-run — payouts already in the database with a Wave entry are skipped.

## Step 6: Schedule daily (Windows Task Scheduler)

Create a file `run_daily.ps1` in this folder:

```powershell
$env:SQUARE_TOKEN     = "your_token_here"
$env:WAVE_TOKEN       = "your_token_here"
$env:WAVE_BUSINESS_ID = "your_id_here"
# ... all WAVE_ACCOUNT env vars ...

cd "C:\Users\lance\OneDrive\Desktop\MidMoConsultant\James Jason Trinton Johnson\Glizzness"
python reconcile.py
```

Then in Task Scheduler:
- Action: `powershell.exe -File "C:\...\run_daily.ps1"`
- Trigger: Daily at 9:00 AM
- (Square deposits for the previous day will be visible by then)

---

## Journal Entry Structure (per payout)

```
DR  Square Settlements Clearing   $XXX.XX   ← anchor (nets to $0 against bank import)
DR  Processing Fees Expense        $X.XX    ← Square's cut
DR  Discounts & Comps              $X.XX    ← (only if discounts exist)
DR  Sales Returns                  $X.XX    ← (only if refunds exist)
    CR  Sales Revenue              $XXX.XX  ← Gross sales
    CR  Tips Income                 $XX.XX  ← (only if tips > $0)
    CR  Sales Tax Payable           $XX.XX  ← (only if tax > $0)
```

One entry per Square payout (not per calendar day).
Multiple payouts on the same day = multiple entries (normal — POS vs Invoice batching).

## Daily Workflow (clearing account approach)

For each "SQUARE INC SQ######" that appears in Wave bank feed:
1. Click the transaction → change category from "Uncategorized Income" to "Square Settlements Clearing"
2. Run `python post_to_wave.py --build <date> && python post_to_wave.py --post <date>`

The API entry debits the clearing account; your bank-import categorization credits it → net $0 in clearing. The full sales split lives in the API journal entry.

## Sync Wave transactions to DB

```powershell
python sync_wave.py          # download all Wave transactions → glizzness.db
python sync_wave.py --status # row counts and date range
python sync_wave.py --list 2025-10   # browse October 2025
```
