import sqlite3

con = sqlite3.connect("ai_mail.db")
cur = con.cursor()

cur.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS ux_out_reply_once
ON conversation_audit(org_id, email_message_id)
WHERE direction='OUT'
  AND email_message_id IS NOT NULL
  AND TRIM(email_message_id) <> '';
""")

con.commit()
con.close()
print("✅ Partial unique index created: ux_out_reply_once (OUT only)")
