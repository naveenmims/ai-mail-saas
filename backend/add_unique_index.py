import sqlite3

con = sqlite3.connect("ai_mail.db")
cur = con.cursor()

# One OUT reply per org per email_message_id
cur.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS ux_out_reply_once
ON conversation_audit(org_id, email_message_id, direction);
""")

con.commit()
con.close()
print("✅ Unique index created: ux_out_reply_once")
