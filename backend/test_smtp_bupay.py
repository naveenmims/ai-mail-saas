import smtplib
email="info@bupay.in"
password="Naveen@1978"
try:
    smtp=smtplib.SMTP_SSL("smtpout.secureserver.net",465,timeout=60)
    smtp.login(email,password)
    print("BUPAY LOGIN SUCCESS")
    smtp.quit()
except Exception as e:
    print("BUPAY LOGIN FAILED:",repr(e))
