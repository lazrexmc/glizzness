-- Glizzness DB — Postgres schema for Supabase
-- Run this once in Supabase Dashboard → SQL Editor

CREATE TABLE IF NOT EXISTS payouts (
    payout_id       TEXT PRIMARY KEY,
    status          TEXT,
    arrival_date    TEXT,
    created_at      TEXT,
    updated_at      TEXT,
    amount_cents    INTEGER,
    currency        TEXT,
    location_id     TEXT,
    destination_id  TEXT,
    raw_json        TEXT
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id          TEXT PRIMARY KEY,
    order_id            TEXT,
    created_at          TEXT,
    updated_at          TEXT,
    status              TEXT,
    source_type         TEXT,
    delay_duration      TEXT,
    delayed_until       TEXT,
    amount_cents        INTEGER,
    tip_cents           INTEGER,
    total_cents         INTEGER,
    fee_cents           INTEGER,
    square_product      TEXT,
    location_id         TEXT,
    expected_arrival    TEXT,
    raw_json            TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    order_id                    TEXT PRIMARY KEY,
    state                       TEXT,
    created_at                  TEXT,
    updated_at                  TEXT,
    location_id                 TEXT,
    total_money_cents           INTEGER,
    total_tax_cents             INTEGER,
    total_discount_cents        INTEGER,
    total_tip_cents             INTEGER,
    total_service_charge_cents  INTEGER,
    net_total_cents             INTEGER,
    raw_json                    TEXT
);

CREATE TABLE IF NOT EXISTS payout_entries (
    entry_id        TEXT PRIMARY KEY,
    payout_id       TEXT NOT NULL REFERENCES payouts(payout_id),
    effective_at    TEXT,
    type            TEXT,
    gross_cents     INTEGER,
    fee_cents       INTEGER,
    net_cents       INTEGER,
    payment_id      TEXT,
    raw_json        TEXT
);

CREATE TABLE IF NOT EXISTS journal_entries (
    payout_id           TEXT PRIMARY KEY,
    arrival_date        TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'staged',
    payout_net_cents    INTEGER,
    gross_sales_cents   INTEGER,
    tips_cents          INTEGER,
    taxes_cents         INTEGER,
    discounts_cents     INTEGER,
    returns_cents       INTEGER,
    fees_cents          INTEGER,
    wave_entry_id       TEXT,
    posted_at           TEXT,
    error_msg           TEXT,
    built_at            TEXT
);

CREATE TABLE IF NOT EXISTS journal_entry_lines (
    id           SERIAL PRIMARY KEY,
    payout_id    TEXT NOT NULL REFERENCES journal_entries(payout_id),
    line_order   INTEGER,
    direction    TEXT,
    account_id   TEXT,
    account_name TEXT,
    amount_cents INTEGER,
    description  TEXT
);

CREATE TABLE IF NOT EXISTS wave_posts (
    payout_id       TEXT PRIMARY KEY,
    wave_entry_id   TEXT,
    posted_at       TEXT
);

CREATE TABLE IF NOT EXISTS wave_accounts (
    account_id      TEXT PRIMARY KEY,
    name            TEXT,
    description     TEXT,
    display_id      TEXT,
    type_name       TEXT,
    type_value      TEXT,
    subtype_name    TEXT,
    subtype_value   TEXT,
    normal_balance  TEXT,
    is_archived     INTEGER,
    currency        TEXT,
    synced_at       TEXT
);

CREATE TABLE IF NOT EXISTS wave_transactions (
    row_key         TEXT PRIMARY KEY,
    txn_date        TEXT,
    description     TEXT,
    account_name    TEXT,
    debit           DOUBLE PRECISION,
    credit          DOUBLE PRECISION,
    balance         DOUBLE PRECISION,
    direction       TEXT,
    net_amount      DOUBLE PRECISION,
    imported_at     TEXT,
    source_file     TEXT
);

CREATE TABLE IF NOT EXISTS loan_payments (
    payment_date    TEXT PRIMARY KEY,
    payment_type    TEXT,
    description     TEXT,
    amount          DOUBLE PRECISION,
    principal       DOUBLE PRECISION,
    interest        DOUBLE PRECISION,
    escrow          DOUBLE PRECISION,
    late_charge     DOUBLE PRECISION,
    balance         DOUBLE PRECISION,
    note            TEXT
);

CREATE TABLE IF NOT EXISTS loan_journal_entries (
    payment_date    TEXT PRIMARY KEY,
    status          TEXT NOT NULL DEFAULT 'staged',
    amount          DOUBLE PRECISION,
    principal       DOUBLE PRECISION,
    interest        DOUBLE PRECISION,
    wave_entry_id   TEXT,
    posted_at       TEXT,
    error_msg       TEXT,
    built_at        TEXT
);

CREATE TABLE IF NOT EXISTS sync_log (
    id              SERIAL PRIMARY KEY,
    synced_at       TEXT,
    date_range      TEXT,
    payouts_found   INTEGER DEFAULT 0,
    payments_found  INTEGER DEFAULT 0,
    orders_found    INTEGER DEFAULT 0,
    entries_found   INTEGER DEFAULT 0,
    errors          TEXT
);

-- Enable RLS on all tables.
-- No policies are created — anon/authenticated keys get zero access.
-- Only the service_role key (used by the dashboard) can read/write.
ALTER TABLE payouts             ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments            ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders              ENABLE ROW LEVEL SECURITY;
ALTER TABLE payout_entries      ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entries     ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entry_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE wave_posts          ENABLE ROW LEVEL SECURITY;
ALTER TABLE wave_accounts       ENABLE ROW LEVEL SECURITY;
ALTER TABLE wave_transactions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE loan_payments       ENABLE ROW LEVEL SECURITY;
ALTER TABLE loan_journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_log            ENABLE ROW LEVEL SECURITY;
