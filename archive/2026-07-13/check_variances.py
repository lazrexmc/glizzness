import sqlite3

conn = sqlite3.connect("glizzness.db")
rows = conn.execute("""
    SELECT p.payout_id, p.arrival_date, p.amount_cents,
           SUM(e.net_cents) as entries_net,
           ABS(p.amount_cents - SUM(e.net_cents)) as variance
    FROM payouts p
    JOIN payout_entries e ON p.payout_id = e.payout_id
    GROUP BY p.payout_id
    HAVING variance > 5
    ORDER BY variance DESC
""").fetchall()

print(f"{len(rows)} payout(s) with variance > 5 cents:")
for r in rows:
    print(f"  {r[0][:20]}  {r[1]}  payout=${r[2]/100:.2f}  entries=${r[3]/100:.2f}  var=${r[4]/100:.2f}")

if not rows:
    total = conn.execute("SELECT COUNT(*) FROM payouts").fetchone()[0]
    print(f"All {total} payouts balance perfectly.")

conn.close()
