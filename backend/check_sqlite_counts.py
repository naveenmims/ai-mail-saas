import sqlite3

con = sqlite3.connect("ai_mail.db")
cur = con.cursor()

tables = ["organizations","email_accounts","users","org_credits","org_usage","conversation_audit","reply_thread_locks"]
for t in tables:
    try:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(t, n)
    except Exception as e:
        print(t, "ERR", e)

con.close()
