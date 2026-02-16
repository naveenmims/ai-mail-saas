import sqlite3

con = sqlite3.connect("ai_mail.db")
cur = con.cursor()

# 1) Add org_id column if missing
cols = [r[1] for r in cur.execute("PRAGMA table_info(replied_messages)").fetchall()]
if "org_id" not in cols:
    cur.execute("ALTER TABLE replied_messages ADD COLUMN org_id INTEGER DEFAULT 1")
    con.commit()
    print("Added org_id column to replied_messages")
else:
    print("org_id column already exists")

# 2) Create index for faster lookup (org_id + message_id)
cur.execute("CREATE INDEX IF NOT EXISTS idx_replied_org_mid ON replied_messages(org_id, message_id)")
con.commit()
print("Index ensured: idx_replied_org_mid")

# Show columns
print("Columns now:", cur.execute("PRAGMA table_info(replied_messages)").fetchall())

con.close()
