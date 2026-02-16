import time
from sqlalchemy.orm import Session

from app.db import engine
from app.models import EmailAccount

POLL_INTERVAL_SECONDS = 15


def main():
    print("Worker started. Polling email accounts...")
    while True:
        try:
            with Session(engine) as db:
                accounts = db.query(EmailAccount).order_by(EmailAccount.id).all()

            if not accounts:
                print("No email accounts configured yet.")
            else:
                for a in accounts:
                    print(f"[poll] org_id={a.org_id} email={a.email} imap={a.imap_host}:{a.imap_port}")

            time.sleep(POLL_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("Worker stopped.")
            return
        except Exception as e:
            print("Worker error:", repr(e))
            time.sleep(5)


if __name__ == "__main__":
    main()
