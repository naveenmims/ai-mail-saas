import os
import sqlite3

p = os.path.abspath("ai_mail.db")
con = sqlite3.connect(p)
cur = con.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER,
    sender TEXT,
    subject TEXT,
    body TEXT,
    ai_reply TEXT,
    message_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

con.commit()
print("OK: conversations table ready")
con.close()
