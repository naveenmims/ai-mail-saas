import sqlite3
con=sqlite3.connect("ai_mail.db")
cur=con.cursor()
cur.execute("PRAGMA table_info(organizations)")
for r in cur.fetchall():
    print(r)
con.close()
import os

db = os.path.join(os.getcwd(), "ai_mail.db")
con = sqlite3.connect(db)
cur = con.cursor()

cur.execute("PRAGMA table_info('organizations')")
cols = cur.fetchall()

print("\nOrganizations columns:\n")
for c in cols:
    print(c)

con.close()
