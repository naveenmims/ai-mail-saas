import os
import sqlite3

p = os.path.abspath("ai_mail.db")
con = sqlite3.connect(p)
cur = con.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS reply_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER,
    message_id TEXT,
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

con.commit()
print("OK: reply_logs table created/exists")
con.close()
