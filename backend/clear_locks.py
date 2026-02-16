import os, sqlite3
db = os.path.join(os.getcwd(), "ai_mail.db")
con = sqlite3.connect(db)
cur = con.cursor()

cur.execute("SELECT COUNT(*) FROM reply_thread_locks")
print("before =", cur.fetchone()[0])

cur.execute("DELETE FROM reply_thread_locks")
con.commit()

cur.execute("SELECT COUNT(*) FROM reply_thread_locks")
print("after  =", cur.fetchone()[0])

con.close()
print("done")
