import sqlite3

DB = "ai_mail.db"
TABLE = "organizations"

queries = [
    "ALTER TABLE organizations ADD COLUMN system_prompt TEXT DEFAULT ''",
    "ALTER TABLE organizations ADD COLUMN kb_text TEXT DEFAULT ''",
    "ALTER TABLE organizations ADD COLUMN website_url TEXT DEFAULT ''",
]

con = sqlite3.connect(DB)
cur = con.cursor()

for q in queries:
    try:
        cur.execute(q)
        print("Added:", q)
    except Exception as e:
        print("Skipped (maybe exists):", e)

con.commit()
con.close()
print("Done.")
