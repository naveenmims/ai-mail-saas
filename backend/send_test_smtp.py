import smtplib
from email.message import EmailMessage

FROM_EMAIL = "info@bupay.in"
FROM_PASS  = "Naveen@1978"   # BuPay mailbox password
TO_EMAIL   = "naveen.mims@gmail.com"

SUBJECT = "Re: Need details about website development"
BODY = """Hi Naveen Chandar Raju,

Thanks for reaching out.

We can help with:
• Website development (modern, mobile-friendly)
• SEO setup + on-page optimization
• Basic performance + security best practices

To share accurate pricing and timeline, please confirm:
1) Website type: business / e-commerce / portfolio / blog
2) Approx pages (Home, About, Services, Contact, etc.)
3) Do you need payment gateway, WhatsApp button, chat, or booking?
4) Preferred timeline (urgent / normal)

Once you share the above, we will send the estimated cost and delivery schedule.

Regards,
BuPay Support
info@bupay.in
"""

msg = EmailMessage()
msg["From"] = FROM_EMAIL
msg["To"] = TO_EMAIL
msg["Subject"] = SUBJECT
msg.set_content(BODY)

SMTP_HOST = "smtpout.secureserver.net"
SMTP_PORT = 465  # SSL

with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as s:
    s.set_debuglevel(1)
    s.ehlo()
    print("Server:", s.noop())
    print("ESMTP features:", s.esmtp_features)
    s.login(FROM_EMAIL, FROM_PASS)
    s.send_message(msg)

print("Sent OK")
