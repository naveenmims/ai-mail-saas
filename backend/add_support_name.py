import sqlite3
con = sqlite3.connect("ai_mail.db")
cur = con.cursor()
cur.execute("ALTER TABLE organizations ADD COLUMN support_name TEXT")
con.commit()
print("OK: support_name column added")
con.close()
