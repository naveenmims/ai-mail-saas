import sqlite3
con = sqlite3.connect("ai_mail.db")
cur = con.cursor()
cur.execute("PRAGMA table_info(organizations)")
print(cur.fetchall())
con.close()
