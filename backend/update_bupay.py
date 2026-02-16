import sqlite3

EMAIL = "info@bupay.in"          # <-- new GoDaddy email
PASSWORD = "Madhavi@1978"   # <-- put bupay.in mailbox password

con = sqlite3.connect("ai_mail.db")
cur = con.cursor()

cur.execute(
    "UPDATE email_accounts SET email=?, imap_username=?, imap_password=? WHERE id=1",
    (EMAIL, EMAIL, PASSWORD),
)

con.commit()

print("Updated row:")
print(cur.execute("SELECT id, email, imap_host, imap_username FROM email_accounts WHERE id=1").fetchone())

con.close()
