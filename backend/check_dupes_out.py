import sqlite3
con = sqlite3.connect("ai_mail.db")
cur = con.cursor()
cur.execute("""
SELECT org_id, email_message_id, COUNT(1) AS c
FROM conversation_audit
WHERE direction='OUT'
  AND email_message_id IS NOT NULL
  AND TRIM(email_message_id) <> ''
GROUP BY org_id, email_message_id
HAVING c > 1
ORDER BY c DESC
LIMIT 20;
""")
print(cur.fetchall())
con.close()
