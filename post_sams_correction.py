#!/usr/bin/env python3
"""
post_sams_correction.py — Post Sam's Club sales tax correction to Wave.

Sam's Club charges sales tax on purchases even though Glizzness is tax-exempt.
This script posts a correcting entry that reclassifies the embedded tax from
COGS - Food/Bev to SamsTax2 - 5.975% (Missouri reduced food rate).

Usage:
  python post_sams_correction.py --preview 16193.60    # show the entry, don't post
  python post_sams_correction.py --post    16193.60    # post to Wave

  Amount is the TOTAL paid to Sam's (from Sam's purchase history).
  Tax is back-calculated: total / (1 + 0.08975) * 0.08975

Env vars required: WAVE_TOKEN, WAVE_BUSINESS_ID
"""

import os, sys, json, requests
from datetime import date, datetime, timezone

WAVE_TOKEN       = os.environ.get("WAVE_TOKEN", "")
WAVE_BUSINESS_ID = os.environ.get("WAVE_BUSINESS_ID", "")

TAX_RATE = 0.05975  # Missouri reduced food rate

# Wave account IDs — env-overridable (WAVE_SAMS_TAX_ID / WAVE_COGS_ID); the defaults are the
# current account references, kept so this annual one-off still runs without extra setup.
SAMS_TAX_ID = os.environ.get("WAVE_SAMS_TAX_ID", "QWNjb3VudDoxOTU4MjYzNjk0NzIyOTAyOTM1O0J1c2luZXNzOmJhMmQwOGFkLTNhNzUtNDkxOC1iZDljLTc4MWFlZmFkMzczNg==")
COGS_ID     = os.environ.get("WAVE_COGS_ID",     "QWNjb3VudDoxOTU4MjY0NTQ0MTQ0OTYwNDg5O0J1c2luZXNzOmJhMmQwOGFkLTNhNzUtNDkxOC1iZDljLTc4MWFlZmFkMzczNg==")

WAVE_GQL = "https://gql.waveapps.com/graphql/public"

CREATE_TRANSACTION = """
mutation ($input: MoneyTransactionCreateInput!) {
  moneyTransactionCreate(input: $input) {
    didSucceed
    inputErrors { code message path }
    transaction { id }
  }
}
"""


def calc_tax(sams_total: float) -> float:
    return round(sams_total / (1 + TAX_RATE) * TAX_RATE, 2)


def preview(sams_total: float, year: int) -> None:
    tax = calc_tax(sams_total)
    true_cogs = round(sams_total - tax, 2)
    print(f"\n  Sam's Club {year} correction")
    print(f"  Sam's total paid : ${sams_total:,.2f}")
    print(f"  Tax rate         : {TAX_RATE*100:.3f}%")
    print(f"  Tax embedded     : ${tax:,.2f}")
    print(f"  True COGS        : ${true_cogs:,.2f}")
    print(f"\n  Journal entry (date: {year}-12-31):")
    print(f"    DR  SamsTax2 - 5.975%       ${tax:,.2f}   reduces sales tax liability")
    print(f"    CR  COGS - Food/Bev         ${tax:,.2f}   removes tax from cost of goods")


def post(sams_total: float, year: int) -> None:
    if not WAVE_TOKEN or not WAVE_BUSINESS_ID:
        print("[error] Set WAVE_TOKEN and WAVE_BUSINESS_ID env vars first.")
        sys.exit(1)

    tax = calc_tax(sams_total)
    entry_date = f"{year}-12-31"

    preview(sams_total, year)

    headers = {"Authorization": f"Bearer {WAVE_TOKEN}", "Content-Type": "application/json"}
    resp = requests.post(
        WAVE_GQL,
        headers=headers,
        json={
            "query": CREATE_TRANSACTION,
            "variables": {
                "input": {
                    "businessId":  WAVE_BUSINESS_ID,
                    "externalId":  f"sams-tax-correction-{year}",
                    "date":        entry_date,
                    "description": f"Sam's Club sales tax correction {year}",
                    "anchor": {
                        "accountId": SAMS_TAX_ID,
                        "amount":    f"{tax:.2f}",
                        "direction": "DEPOSIT",
                    },
                    "lineItems": [
                        {
                            "accountId":   COGS_ID,
                            "amount":      f"{tax:.2f}",
                            "balance":     "CREDIT",
                            "description": f"Remove embedded Sam's Club sales tax ({TAX_RATE*100:.3f}% of ${sams_total:,.2f})",
                        }
                    ],
                }
            },
        },
    )

    if not resp.ok:
        print(f"\n[Wave HTTP {resp.status_code}] {resp.text[:400]}")
        sys.exit(1)

    result = resp.json()
    gql = (result.get("data") or {}).get("moneyTransactionCreate", {})

    if gql.get("didSucceed"):
        wave_id = (gql.get("transaction") or {}).get("id", "")
        print(f"\n  [posted] Wave transaction ID: {wave_id}")
    else:
        errors = gql.get("inputErrors") or result.get("errors") or []
        print(f"\n  [error] {json.dumps(errors)[:300]}")


def main() -> None:
    args = sys.argv[1:]

    if len(args) < 2:
        print(__doc__)
        sys.exit(0)

    command    = args[0]
    sams_total = float(args[1])
    year       = int(args[2]) if len(args) > 2 else date.today().year

    if command == "--preview":
        preview(sams_total, year)
    elif command == "--post":
        post(sams_total, year)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
