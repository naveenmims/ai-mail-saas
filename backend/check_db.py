import os
import sqlite3

p = os.path.abspath("ai_mail.db")
print("DB:", p)

con = sqlite3.connect(p)
cur = con.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
print("Tables:", cur.fetchall())

con.close()
