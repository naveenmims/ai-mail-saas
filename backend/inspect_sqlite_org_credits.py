import sqlite3
con=sqlite3.connect("ai_mail.db")
cur=con.cursor()
print("SQLite org_credits columns:")
for r in cur.execute("PRAGMA table_info(org_credits)"):
    print(r)
print("\nSample rows:")
for r in cur.execute("SELECT * FROM org_credits LIMIT 5"):
    print(r)
con.close()
