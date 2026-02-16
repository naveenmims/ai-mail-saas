import sqlite3
con = sqlite3.connect("ai_mail.db")
cur = con.cursor()
cur.execute("UPDATE organizations SET support_name=? WHERE id=?", ("BatterUpD Foods Support", 2))
con.commit()
print("Updated rows:", cur.rowcount)
con.close()
