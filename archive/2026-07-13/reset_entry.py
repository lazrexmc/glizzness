import sqlite3
conn = sqlite3.connect("glizzness.db")
rows = conn.execute(
    "SELECT payout_id, arrival_date, status FROM journal_entries WHERE arrival_date = '2026-06-08'"
).fetchall()
for pid, date, status in rows:
    print(f"Resetting: {pid}  ({date})  was: {status}")
    conn.execute(
        "UPDATE journal_entries SET status='staged', wave_entry_id=NULL, posted_at=NULL, error_msg=NULL WHERE payout_id=?",
        (pid,)
    )
    conn.execute("DELETE FROM journal_entry_lines WHERE payout_id=?", (pid,))
conn.commit()
conn.close()
print("Done.")
