import sqlite3

DB = "ai_mail.db"

con = sqlite3.connect(DB)
cur = con.cursor()

def add_col(table, coldef):
    # coldef example: "system_prompt TEXT"
    col = coldef.split()[0]
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    if col in cols:
        print(f"OK: {table}.{col} already exists")
        return
    cur.execute(f"ALTER TABLE {table} ADD COLUMN {coldef}")
    print(f"ADDED: {table}.{coldef}")

add_col("organizations", "support_name TEXT")
add_col("organizations", "support_email TEXT")
add_col("organizations", "website TEXT")
add_col("organizations", "kb_text TEXT")              # knowledge base text (services, FAQs, etc.)
add_col("organizations", "system_prompt TEXT")        # per-org system role
add_col("organizations", "auto_reply INTEGER DEFAULT 1")
add_col("organizations", "max_replies_per_hour INTEGER DEFAULT 10")

con.commit()
con.close()
print("DONE: organizations upgraded")
