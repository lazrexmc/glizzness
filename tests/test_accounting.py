"""Tests for the accounting pipeline (audit remediation, 2026-06-18).

Pure-logic tests only — no Square/Wave/Supabase network. Run: `pytest tests/`.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import sync
import auth
import money


# ---- Audit finding #11/#3: money parses to integer cents, fails loud on garbage ----

def test_blank_is_zero_cents():
    assert money.parse_money_to_cents("") == 0
    assert money.parse_money_to_cents("   ") == 0
    assert money.parse_money_to_cents(None) == 0

def test_plain_dollars_to_cents():
    assert money.parse_money_to_cents("12") == 1200

def test_decimal_dollars_to_cents():
    assert money.parse_money_to_cents("1234.56") == 123456

def test_currency_symbols_and_commas_stripped():
    assert money.parse_money_to_cents("$1,234.56") == 123456

def test_parentheses_mean_negative():
    assert money.parse_money_to_cents("(5.00)") == -500

def test_leading_minus_is_negative():
    assert money.parse_money_to_cents("-5.00") == -500

def test_no_binary_float_drift():
    # 0.10 and 19.99 are classic float-representation traps.
    assert money.parse_money_to_cents("0.10") == 10
    assert money.parse_money_to_cents("19.99") == 1999

def test_half_cent_rounds_half_up():
    assert money.parse_money_to_cents("0.005") == 1

def test_garbage_raises_valueerror():
    with pytest.raises(ValueError):
        money.parse_money_to_cents("not-a-number")


# ---- Audit finding #2: dashboard auth must fail CLOSED ----

def test_no_password_and_no_override_is_blocked():
    # The dangerous case: deployed with no password configured -> deny access.
    assert auth.auth_gate_decision("", allow_insecure=False) == "blocked"


def test_password_set_requires_login():
    assert auth.auth_gate_decision("hunter2", allow_insecure=False) == "require_password"


def test_no_password_with_explicit_local_override_opens():
    assert auth.auth_gate_decision("", allow_insecure=True) == "open_insecure"


# ---- Audit finding #1/#4: error rows must never be selected for posting ----

def test_error_status_is_not_postable():
    assert sync.is_postable("error") is False


def test_staged_status_is_postable():
    assert sync.is_postable("staged") is True


def test_posted_status_is_not_postable():
    assert sync.is_postable("posted") is False
