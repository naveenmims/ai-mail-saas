import os, sqlite3

db = os.path.join(os.getcwd(), "ai_mail.db")
print("DB:", db)

con = sqlite3.connect(db)
cur = con.cursor()

cur.execute("DROP TABLE IF EXISTS worker_status")
cur.execute("""
CREATE TABLE worker_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id TEXT NOT NULL UNIQUE,
    last_run_at TEXT,
    last_email_processed_at TEXT,
    last_email_message_id TEXT,
    last_thread_key TEXT,
    lock_health_ok INTEGER NOT NULL DEFAULT 1,
    credits_health_ok INTEGER NOT NULL DEFAULT 1,
    last_error TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("DROP TABLE IF EXISTS conversation_audit")
cur.execute("""
CREATE TABLE conversation_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL,
    thread_key TEXT NOT NULL,
    customer_email TEXT,
    subject TEXT,
    direction TEXT NOT NULL,
    body_text TEXT,
    body_html TEXT,
    email_message_id TEXT,
    in_reply_to TEXT,
    references_header TEXT,
    ai_model TEXT,
    ai_tokens_in INTEGER,
    ai_tokens_out INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("CREATE INDEX IF NOT EXISTS ix_conversation_audit_org_id ON conversation_audit(org_id)")
cur.execute("CREATE INDEX IF NOT EXISTS ix_conversation_audit_thread_key ON conversation_audit(thread_key)")
cur.execute("CREATE INDEX IF NOT EXISTS ix_conversation_audit_created_at ON conversation_audit(created_at)")
cur.execute("CREATE INDEX IF NOT EXISTS ix_conversation_audit_org_thread_created ON conversation_audit(org_id, thread_key, created_at)")
cur.execute("CREATE INDEX IF NOT EXISTS ix_worker_status_worker_id ON worker_status(worker_id)")

con.commit()
con.close()
print("✅ Done.")
