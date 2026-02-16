import sqlite3
con = sqlite3.connect("ai_mail.db")
cur = con.cursor()
cur.execute("SELECT id, name, support_name FROM organizations ORDER BY id")
print(cur.fetchall())
con.close()
