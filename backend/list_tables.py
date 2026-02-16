import sqlite3
from pathlib import Path

p = Path("ai_mail.db")
print("DB exists:", p.exists(), "->", p.resolve())

con = sqlite3.connect(p)
cur = con.cursor()

print("TABLES:")
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    print(" -", row[0])

con.close()
