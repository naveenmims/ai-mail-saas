import sqlite3
con = sqlite3.connect("ai_mail.db")
cur = con.cursor()
rows = cur.execute("""
SELECT id, created_at, thread_key, direction, subject, customer_email
FROM conversation_audit
WHERE org_id=3
ORDER BY id DESC
LIMIT 10
""").fetchall()
for r in rows:
    print(r)
con.close()
