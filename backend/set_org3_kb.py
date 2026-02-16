import sqlite3, textwrap

ORG_ID = 3
DB = "ai_mail.db"

kb_text = textwrap.dedent("""
PASTE VSPAZE WEBSITE KB TEXT HERE.
Include: courses, durations, fees (if shown), contact info, address, enrollment steps, refund policy (if any), timings.
If a detail is not present on website, leave it out.
""").strip()

con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("UPDATE organizations SET kb_text=? WHERE id=?", (kb_text, ORG_ID))
con.commit()
con.close()
print("KB updated for org", ORG_ID)
