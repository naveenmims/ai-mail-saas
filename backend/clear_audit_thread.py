import os, sqlite3

ORG_ID = 3
THREAD = "m:<0jmreLl9RSS1OnK1wGGhmg@geopod-ismtpd-8>"

db = os.path.join(os.getcwd(), "ai_mail.db")
con = sqlite3.connect(db)
cur = con.cursor()

cur.execute("SELECT COUNT(*) FROM conversation_audit WHERE org_id=? AND thread_key=?", (ORG_ID, THREAD))
print("before =", cur.fetchone()[0])

cur.execute("DELETE FROM conversation_audit WHERE org_id=? AND thread_key=?", (ORG_ID, THREAD))
con.commit()

cur.execute("SELECT COUNT(*) FROM conversation_audit WHERE org_id=? AND thread_key=?", (ORG_ID, THREAD))
print("after  =", cur.fetchone()[0])

con.close()
print("done")
