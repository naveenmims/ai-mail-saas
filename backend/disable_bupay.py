import sqlite3
con = sqlite3.connect("ai_mail.db")
cur = con.cursor()
cur.execute("UPDATE organizations SET auto_reply=0 WHERE id=1")
con.commit()
print("BuPay auto_reply DISABLED")
con.close()
