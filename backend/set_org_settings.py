import sqlite3

DB="ai_mail.db"
con=sqlite3.connect(DB)
cur=con.cursor()

def upd(org_id, support_name=None, support_email=None, website=None, kb_text=None, system_prompt=None, auto_reply=None, max_replies_per_hour=None):
    fields=[]
    vals=[]
    if support_name is not None:
        fields.append("support_name=?"); vals.append(support_name)
    if support_email is not None:
        fields.append("support_email=?"); vals.append(support_email)
    if website is not None:
        fields.append("website=?"); vals.append(website)
    if kb_text is not None:
        fields.append("kb_text=?"); vals.append(kb_text)
    if system_prompt is not None:
        fields.append("system_prompt=?"); vals.append(system_prompt)
    if auto_reply is not None:
        fields.append("auto_reply=?"); vals.append(int(auto_reply))
    if max_replies_per_hour is not None:
        fields.append("max_replies_per_hour=?"); vals.append(int(max_replies_per_hour))

    if not fields:
        return

    vals.append(org_id)
    sql = "UPDATE organizations SET " + ", ".join(fields) + " WHERE id=?"
    cur.execute(sql, vals)
    print(f"Updated org_id={org_id}, rows={cur.rowcount}")

# -----------------------------
# Global Safe System Prompt (A,B,C)
# -----------------------------
SAFE_SYSTEM_PROMPT = """You are replying as the company's official email support.

Rules:
A) DO NOT invent or assume facts (addresses, prices, outlet names, availability on Swiggy/Zomato, phone numbers, policies).
B) If required info is missing, ask 1–3 clear questions.
C) Use ONLY the provided Knowledge Base and website details if present; otherwise ask the customer for details.

If the email looks like marketing/newsletter/security alert/OTP/invoice/login alert, do NOT reply.
Keep concise and professional.
"""

# -----------------------------
# BuPay (org_id=1)
# Update details if needed
# -----------------------------
bupay_kb = """BuPay - Knowledge Base (edit me):
- What services you offer (payments, integrations, support etc.)
- Working hours
- Contact/phone (only if confirmed)
- Pricing (only if confirmed)
"""

upd(
    org_id=1,
    support_name="BuPay Support",
    support_email="info@bupay.in",
    website="https://bupay.in",
    kb_text=bupay_kb,
    system_prompt=SAFE_SYSTEM_PROMPT,
    auto_reply=1,
    max_replies_per_hour=10
)

# -----------------------------
# BatterUpD (org_id=2)
# Update details if needed
# -----------------------------
batterupd_kb = """BatterUpD Foods - Knowledge Base (edit me):
- Authorised outlet onboarding requirements (location, daily sales, freezer availability)
- Order platforms (ONLY if confirmed; otherwise ask)
- Outlet addresses (ONLY if confirmed; otherwise ask area/landmark)
"""

upd(
    org_id=2,
    support_name="BatterUpD Foods Support",
    support_email="customercare@batterupdfoods.com",
    website="https://www.batterupdfoods.com",
    kb_text=batterupd_kb,
    system_prompt=SAFE_SYSTEM_PROMPT,
    auto_reply=1,
    max_replies_per_hour=10
)

con.commit()
con.close()
print("DONE")
