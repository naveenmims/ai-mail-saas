from sqlalchemy.orm import Session
from app.db import engine
from app.models import EmailAccount

ORG_ID = 2
EMAIL = "customercare@batterupdfoods.com"
PASSWORD = "businessno.one"

db = Session(engine)

acct = EmailAccount(
    org_id=ORG_ID,
    label="Primary",
    email=EMAIL,
    imap_host="imap.secureserver.net",
    imap_port=993,
    imap_username=EMAIL,
    imap_password=PASSWORD,
    sendgrid_api_key="",
    from_name="Tenant2 Support"
)

db.add(acct)
db.commit()

print("Inserted email account:", acct.id, acct.org_id, acct.email)
db.close()
