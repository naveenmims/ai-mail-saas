import sqlite3

con = sqlite3.connect("ai_mail.db")
cur = con.cursor()

print("\n--- ALL TABLES ---")
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print(tables)

print("\n--- TABLES WITH reply / conversation ---")
cur.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type='table'
      AND (name LIKE '%reply%' OR name LIKE '%repl%' OR name LIKE '%conversation%')
    ORDER BY name
""")
print(cur.fetchall())

con.close()
