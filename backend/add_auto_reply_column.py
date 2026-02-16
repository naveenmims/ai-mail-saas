import os
import sqlite3

p = os.path.abspath("ai_mail.db")
con = sqlite3.connect(p)
cur = con.cursor()

cur.execute("ALTER TABLE organizations ADD COLUMN auto_reply INTEGER DEFAULT 1")

con.commit()
print("OK: auto_reply column added")
con.close()
