"""Dashboard auth-gate policy (import-safe; no Streamlit at import time).

Audit 2026-06-18 finding #2: the dashboard previously skipped its password gate
entirely whenever APP_PASSWORD was unset, so a misconfigured deployment exposed
service-role-backed actions. The gate must FAIL CLOSED: no password configured =>
no access, unless an operator explicitly opts into insecure local dev.
"""


def auth_gate_decision(app_password: str, allow_insecure: bool) -> str:
    """How the dashboard should gate access.

    Returns one of:
      "require_password" — a password is configured; prompt for it.
      "open_insecure"    — no password, but the operator explicitly allowed it
                           (local dev only).
      "blocked"          — no password and no explicit override: deny access.
    """
    if app_password:
        return "require_password"
    if allow_insecure:
        return "open_insecure"
    return "blocked"
