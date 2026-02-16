import sqlite3

DB = "ai_mail.db"

con = sqlite3.connect(DB)
cur = con.cursor()

# Show top duplicate OUT groups
cur.execute("""
SELECT org_id, email_message_id, COUNT(1) AS c
FROM conversation_audit
WHERE direction='OUT'
  AND email_message_id IS NOT NULL
  AND TRIM(email_message_id) <> ''
GROUP BY org_id, email_message_id
HAVING c > 1
ORDER BY c DESC
LIMIT 50;
""")
dupes = cur.fetchall()
print("Duplicate OUT groups (org_id, email_message_id, count):")
for row in dupes:
    print(row)

# Delete all but the smallest id for each duplicate group (OUT only)
cur.execute("""
DELETE FROM conversation_audit
WHERE direction='OUT'
  AND email_message_id IS NOT NULL
  AND TRIM(email_message_id) <> ''
  AND id NOT IN (
    SELECT MIN(id)
    FROM conversation_audit
    WHERE direction='OUT'
      AND email_message_id IS NOT NULL
      AND TRIM(email_message_id) <> ''
    GROUP BY org_id, email_message_id
  );
""")

deleted = cur.rowcount
con.commit()
con.close()

print(f"\n✅ Deleted duplicate OUT rows: {deleted}")
print("Now you can create the unique index.")
