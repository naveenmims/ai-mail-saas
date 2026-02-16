import sqlite3

con = sqlite3.connect("ai_mail.db")
cur = con.cursor()

print("COLUMNS:")
for row in cur.execute("PRAGMA table_info(organizations)"):
    print(" -", row)

print("\nROWS:")
for row in cur.execute("SELECT * FROM organizations"):
    print(row)

con.close()
