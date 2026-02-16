import sqlite3

con = sqlite3.connect("ai_mail.db")
cur = con.cursor()

# Create new table with correct constraint
cur.execute("""
CREATE TABLE IF NOT EXISTS replied_messages_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL,
    message_id TEXT NOT NULL,
    UNIQUE(org_id, message_id)
)
""")

# Copy data from old table (if old exists)
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='replied_messages'")
if cur.fetchone():
    rows = cur.execute("SELECT org_id, message_id FROM replied_messages").fetchall()
    for org_id, mid in rows:
        try:
            cur.execute(
                "INSERT OR IGNORE INTO replied_messages_new (org_id, message_id) VALUES (?, ?)",
                (org_id, mid)
            )
        except Exception:
            pass

# Drop old and rename new
cur.execute("DROP TABLE replied_messages")
cur.execute("ALTER TABLE replied_messages_new RENAME TO replied_messages")

# Recreate index
cur.execute("CREATE INDEX IF NOT EXISTS idx_replied_org_mid ON replied_messages(org_id, message_id)")

con.commit()

print("Rebuilt replied_messages with UNIQUE(org_id, message_id)")
print("Columns:", cur.execute("PRAGMA table_info(replied_messages)").fetchall())
print("Top rows:", cur.execute("SELECT id, org_id, message_id FROM replied_messages ORDER BY id DESC LIMIT 5").fetchall())

con.close()
