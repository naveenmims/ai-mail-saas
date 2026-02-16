import smtplib

email = "customercare@batterupdfoods.com"
password = "businessno.one" 

try:
    smtp = smtplib.SMTP_SSL("smtpout.secureserver.net", 465, timeout=60)
    smtp.login(email, password)
    print("LOGIN SUCCESS")
    smtp.quit()
except Exception as e:
    print("LOGIN FAILED:", repr(e))
