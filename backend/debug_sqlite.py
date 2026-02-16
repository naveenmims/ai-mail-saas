import os
import sqlite3

db = os.path.join(os.getcwd(), "ai_mail.db")
con = sqlite3.connect(db)
cur = con.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("tables =", tables)

lock_like = [x for x in tables if "lock" in x.lower() or "thread" in x.lower()]
print("lock_like_tables =", lock_like)

con.close()
print("done")
