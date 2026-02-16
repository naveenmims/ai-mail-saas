import sqlite3
con = sqlite3.connect("ai_mail.db")
cur = con.cursor()
cur.execute("UPDATE organizations SET auto_reply = 0 WHERE id = 2")
con.commit()
print("BatterUpD auto_reply disabled")
con.close()
