"""Money parsing — integer cents, no float drift, loud on garbage.

Audit 2026-06-18 findings #3/#11: the CSV/loan import paths parsed money with
`float(...)` and silently coerced any parse failure to 0.0, so a malformed cell
became $0.00 and float arithmetic could drift pennies. This parser returns exact
integer cents via Decimal, treats only blank/whitespace as 0, and raises
ValueError on anything non-numeric so bad data fails loudly instead of silently.
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


def parse_money_to_cents(value) -> int:
    """Parse a money string to an integer number of cents.

    Accepts blank/None (-> 0), plain/decimal dollars, `$`/`,` formatting,
    a leading `-`, and accounting `(parentheses)` for negatives. Raises
    ValueError on any non-empty value that isn't a finite number.
    """
    s = ("" if value is None else str(value)).strip()
    if not s:
        return 0

    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    s = s.replace("$", "").replace(",", "").strip()
    if s.startswith("-"):
        negative = True
        s = s[1:].strip()
    if not s:
        return 0

    try:
        dollars = Decimal(s)
    except InvalidOperation:
        raise ValueError(f"Cannot parse money value: {value!r}")
    if not dollars.is_finite():
        raise ValueError(f"Non-finite money value: {value!r}")

    cents = int((dollars * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return -cents if negative else cents
