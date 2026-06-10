import sqlite3
conn = sqlite3.connect("glizzness.db")

print("=== 2026 payouts (most recent 10) ===")
for r in conn.execute("""
    SELECT payout_id, arrival_date, amount_cents,
           (SELECT COUNT(*) FROM payout_entries e WHERE e.payout_id = p.payout_id) as entry_count
    FROM payouts p
    WHERE arrival_date >= '2026-01-01'
    ORDER BY arrival_date DESC
    LIMIT 10
"""):
    print(f"  {r[1]}  ${r[2]/100:>8.2f}  {r[3]} entries  {r[0][:20]}")

print()
print("=== Payouts June 1-10, 2026 ===")
rows = conn.execute("""
    SELECT payout_id, arrival_date, amount_cents
    FROM payouts
    WHERE arrival_date BETWEEN '2026-06-01' AND '2026-06-10'
    ORDER BY arrival_date
""").fetchall()
if rows:
    for r in rows:
        print(f"  {r[1]}  ${r[2]/100:.2f}  {r[0]}")
else:
    print("  No payouts found in that window")

print()
print("=== Most recent 5 payout arrival dates in DB ===")
for r in conn.execute("SELECT DISTINCT arrival_date FROM payouts ORDER BY arrival_date DESC LIMIT 5"):
    print(f"  {r[0]}")

conn.close()
