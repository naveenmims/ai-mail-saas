import sqlite3
con = sqlite3.connect("ai_mail.db")
cur = con.cursor()
cur.execute("UPDATE organizations SET auto_reply=1 WHERE id=2")
con.commit()
print("BatterUpD auto_reply ENABLED")
con.close()
