import sqlite3, os
p=os.path.abspath("ai_mail.db")
con=sqlite3.connect(p)
cur=con.cursor()
cur.execute("SELECT id,name,auto_reply FROM organizations ORDER BY id")
print(cur.fetchall())
con.close()
