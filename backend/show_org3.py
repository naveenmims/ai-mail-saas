import sqlite3

con = sqlite3.connect("ai_mail.db")
cur = con.cursor()

row = cur.execute("""
SELECT id, name, support_email, website, website_url,
       LENGTH(system_prompt), LENGTH(kb_text)
FROM organizations
WHERE id = 3
""").fetchone()

print(row)
con.close()
