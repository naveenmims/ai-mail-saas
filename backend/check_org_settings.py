import sqlite3
con=sqlite3.connect("ai_mail.db")
cur=con.cursor()
cur.execute("SELECT id, name, support_name, support_email, website, auto_reply, max_replies_per_hour FROM organizations ORDER BY id")
for r in cur.fetchall():
    print(r)
con.close()
