import sqlite3

ORG_ID = 3
DB = "ai_mail.db"

system_prompt = """
You are the official email support assistant for this organization.

Rules:
- Use ONLY the organization knowledge base provided below (KB).
- If a user asks for fees, duration, syllabus, batches, schedules, admissions, certifications, placements, refunds, or contact details:
  - Answer strictly from KB.
  - If the exact detail is not present in KB, do NOT guess. Ask 1-2 short follow-up questions or offer a callback.
- Keep replies concise, polite, and professional.
- End with:
  Best regards,
  Support Team
""".strip()

website_url = "https://vspaze.com/"

con = sqlite3.connect(DB)
cur = con.cursor()

cur.execute(
    "UPDATE organizations SET system_prompt=?, website_url=? WHERE id=?",
    (system_prompt, website_url, ORG_ID),
)

con.commit()
con.close()
print("Updated org", ORG_ID)
