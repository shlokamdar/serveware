"""Emails pipeline status via Gmail SMTP. Never fails the build."""
import os
import smtplib
import sys
from email.message import EmailMessage

status = sys.argv[1] if len(sys.argv) > 1 else "UNKNOWN"
user = os.environ.get("SMTP_USER")
password = os.environ.get("SMTP_PASSWORD")
to = os.environ.get("ALERT_EMAIL_TO") or user
if not (user and password):
    print("SMTP credentials not set; skipping notification")
    sys.exit(0)

build = os.environ.get("BUILD_NUMBER", "?")
version = os.environ.get("VERSION", "?")
commit = os.environ.get("GIT_SHORT", "?")
url = os.environ.get("BUILD_URL", "")

msg = EmailMessage()
msg["Subject"] = f"[Jenkins] ServeWare pipeline {status} - build #{build} v{version}"
msg["From"] = f"ServeWare CI <{user}>"
msg["To"] = to
msg.set_content(
    f"Pipeline result: {status}\n"
    f"Build: #{build}\nVersion: {version}\nCommit: {commit}\n\n"
    f"Console & reports: {url}\n"
)

try:
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
    print(f"Notification emailed to {to}")
except Exception as exc:  # noqa: BLE001
    print(f"Email notification failed: {exc}")
