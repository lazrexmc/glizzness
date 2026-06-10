import sqlite3
conn = sqlite3.connect("glizzness.db")
rows = conn.execute(
    "SELECT payout_id, arrival_date FROM journal_entries WHERE status = 'error'"
).fetchall()
for pid, date in rows:
    print(f"Resetting: {date}  {pid}")
    conn.execute(
        "UPDATE journal_entries SET status='staged', wave_entry_id=NULL, posted_at=NULL, error_msg=NULL WHERE payout_id=?",
        (pid,)
    )
    conn.execute("DELETE FROM journal_entry_lines WHERE payout_id=?", (pid,))
conn.commit()
conn.close()
print(f"Done. Reset {len(rows)} entries.")
