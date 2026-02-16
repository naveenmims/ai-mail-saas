import sqlite3

con = sqlite3.connect("ai_mail.db")
cur = con.cursor()

cols = cur.execute("PRAGMA table_info(organizations)").fetchall()
print([c[1] for c in cols])

con.close()
