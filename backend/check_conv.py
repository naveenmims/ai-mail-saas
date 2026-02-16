import sqlite3

con = sqlite3.connect("ai_mail.db")
cur = con.cursor()

rows = cur.execute("""
SELECT id, org_id, sender, created_at
FROM conversations
WHERE lower(sender)=lower(?)
ORDER BY id DESC
LIMIT 5
""", ("deepakpatel.webmaster@outlook.com",)).fetchall()

print("ROWS:", rows)

con.close()
