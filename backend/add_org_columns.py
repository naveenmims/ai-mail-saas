import sqlite3

con = sqlite3.connect("app.db")
cur = con.cursor()

queries = [
    "ALTER TABLE orgs ADD COLUMN system_prompt TEXT DEFAULT ''",
    "ALTER TABLE orgs ADD COLUMN kb_text TEXT DEFAULT ''",
    "ALTER TABLE orgs ADD COLUMN website_url TEXT DEFAULT ''",
]

for q in queries:
    try:
        cur.execute(q)
        print("Added:", q)
    except Exception as e:
        print("Skipped (maybe exists):", e)

con.commit()
con.close()

print("Done.")
