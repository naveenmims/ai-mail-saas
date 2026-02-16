import sqlite3
con=sqlite3.connect("ai_mail.db")
cur=con.cursor()
print("SQLite reply_thread_locks columns:")
for r in cur.execute("PRAGMA table_info(reply_thread_locks)"):
    print(r)
print("\nSample rows:")
for r in cur.execute("SELECT * FROM reply_thread_locks LIMIT 5"):
    print(r)
con.close()
