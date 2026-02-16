import sqlite3

DB = "ai_mail.db"

con = sqlite3.connect(DB)
cur = con.cursor()

tables = cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()

print("Tables in", DB)
for t in tables:
    print(" -", t[0])

con.close()
