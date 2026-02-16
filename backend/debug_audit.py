import os, sqlite3

ORG_ID = 3
THREAD = "m:<0jmreLl9RSS1OnK1wGGhmg@geopod-ismtpd-8>"
MSGID  = "<CAFqTUby=YMw=5vT3doLdGf2G1gvXP-t0OtP=JVFKycNNwpU2Wg@mail.gmail.com>"

db = os.path.join(os.getcwd(), "ai_mail.db")
con = sqlite3.connect(db)
con.row_factory = sqlite3.Row
cur = con.cursor()

# Print schema (so we know column names)
cur.execute("PRAGMA table_info(conversation_audit)")
cols = [r["name"] for r in cur.fetchall()]
print("conversation_audit columns =", cols)

# Show matching rows (by thread_key OR message_id)
q = "SELECT * FROM conversation_audit WHERE org_id=? AND (thread_key=? OR message_id=?) ORDER BY rowid DESC LIMIT 20"
cur.execute(q, (ORG_ID, THREAD, MSGID))
rows = cur.fetchall()
print("matched rows =", len(rows))

for r in rows:
    # print only available cols safely
    d = dict(r)
    print("----")
    for k in cols:
        if k in d and d[k] is not None:
            print(f"{k} = {d[k]}")

con.close()
print("done")
