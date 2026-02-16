import sqlite3

con = sqlite3.connect("ai_mail.db")
cur = con.cursor()

# Find duplicates of outgoing replies for the same email_message_id
cur.execute("""
SELECT email_message_id, COUNT(1) AS c
FROM conversation_audit
WHERE direction = 'OUT'
  AND email_message_id IS NOT NULL
  AND TRIM(email_message_id) <> ''
GROUP BY email_message_id
HAVING c > 1
ORDER BY c DESC
LIMIT 20;
""")

rows = cur.fetchall()
print("DUPLICATE OUT replies (same email_message_id):")
for r in rows:
    print(r)

con.close()
