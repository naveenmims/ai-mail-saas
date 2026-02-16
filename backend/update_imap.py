import sqlite3

DB = "ai_mail.db"

con = sqlite3.connect(DB)
cur = con.cursor()

print("BEFORE:")
for row in cur.execute("SELECT id, imap_host, imap_port FROM email_accounts WHERE id=1"):
    print(row)

cur.execute(
    "UPDATE email_accounts SET imap_host=?, imap_port=? WHERE id=1",
    ("imap.secureserver.net", 993),
)
con.commit()

print("\nAFTER:")
for row in cur.execute("SELECT id, imap_host, imap_port FROM email_accounts WHERE id=1"):
    print(row)

con.close()
