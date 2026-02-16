from sqlalchemy.orm import Session
from app.db import engine
from app.models import EmailAccount

EMAIL = "info@bupay.in"
PASSWORD = "Naveen@1978"   # <-- paste the NEW password here

db = Session(engine)

acct = EmailAccount(
    org_id=1,
    label="Primary",
    email=EMAIL,
    imap_host="imap.secureserver.net",
    imap_port=993,
    imap_username=EMAIL,
    imap_password=PASSWORD,
    sendgrid_api_key="",
    from_name="BuPay Support"
)

db.add(acct)
db.commit()

print("Inserted email account:", acct.id, acct.email)

db.close()
