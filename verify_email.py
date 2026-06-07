import sys
import os

# Add the project root to sys.path so we can import utils
project_root = r"c:\Users\leoma\Downloads\sepsis sk 1\Sepsis SK"
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    from utils.mailer import send_real_email
    import json

    print("--- AI Hospital Email Verification ---")
    
    # Check if config exists
    config_path = os.path.join(project_root, 'email_config.json')
    if not os.path.exists(config_path):
        print(f"[!] Config file not found at {config_path}")
        sys.exit(1)

    with open(config_path, 'r') as f:
        config = json.load(f)

    print(f"Sender: {config.get('sender_email')}")
    print(f"Receiver: {config.get('receiver_email')}")
    print(f"Alerts Enabled: {config.get('alert_enabled')}")
    
    if config.get('sender_password') == "YOUR_APP_PASSWORD_HERE":
        print("\n[!] STATUS: SETUP INCOMPLETE")
        print("    You must replace 'YOUR_APP_PASSWORD_HERE' in email_config.json with your Google App Password.")
    else:
        print("\n[+] STATUS: CONFIG UPDATED")
        print("    Attempting to send test email...")
        result = send_real_email("AI Hospital Test", "This is a verification email from your AI Hospital system.")
        print(f"    Result: {result}")

except Exception as e:
    print(f"[!] Error during verification: {e}")
