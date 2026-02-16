import sqlite3

con = sqlite3.connect("ai_mail.db")
cur = con.cursor()

tables = cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()

print("Tables:", tables)

con.close()
