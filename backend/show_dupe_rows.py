import sqlite3

MSG_ID = "<PUT_MESSAGE_ID_HERE>"

con = sqlite3.connect("ai_mail.db")
cur = con.cursor()

cur.execute("""
SELECT id, org_id, direction, email_message_id, thread_key, created_at, subject
FROM conversation_audit
WHERE email_message_id = ?
ORDER BY created_at ASC;
""", (MSG_ID,))

for row in cur.fetchall():
    print(row)

con.close()
