import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load Email Configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'email_config.json')

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    return {}

def send_real_email(subject, body, is_html=False):
    """
    Sends a real email using SMTP configuration from email_config.json.
    """
    config = load_config()
    if not config.get("alert_enabled", False):
        return "Disabled"

    sender_email = config.get("sender_email")
    sender_password = config.get("sender_password")
    receiver_email = config.get("receiver_email")
    smtp_server = config.get("smtp_server", "smtp.gmail.com")
    smtp_port = config.get("smtp_port", 587)

    if not all([sender_email, sender_password, receiver_email]):
        print("[!] Email configuration incomplete. Check sender_email, sender_password, and receiver_email.")
        return "Config Error"

    if sender_password == "YOUR_APP_PASSWORD_HERE":
        print("[!] Placeholder password detected. Please update email_config.json with a real App Password.")
        return "Password Not Set"

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html' if is_html else 'plain'))

        # Connect to server and send
        print(f"[*] Connecting to SMTP server {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls() # Secure the connection
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        print(f"[SUCCESS] AI ALERT EMAIL DISPATCHED to {receiver_email}")
        return "Sent"
    except Exception as e:
        print(f"[CRITICAL ERROR] SMTP Dispatch Failed: {e}")
        return f"Error: {str(e)}"
