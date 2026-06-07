import json
import sqlite3
import os
import threading
import time
from datetime import datetime, timedelta
from utils.database import get_db_connection
from utils.mailer import send_real_email

# Load Email Configuration
EMAIL_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'email_config.json')
EMAIL_CONFIG = {}
if os.path.exists(EMAIL_CONFIG_PATH):
    with open(EMAIL_CONFIG_PATH, 'r') as f:
        EMAIL_CONFIG = json.load(f)

def simulate_email(patient_id, disease, risk, level):
    """Sends a real automated email to hospital staff."""
    subject = f"AI Hospital Alert - {level}: {disease} Risk"
    body = f"""
    <h3>AI Hospital Alert - High Risk Patient</h3>
    <p><b>Patient ID:</b> {patient_id}</p>
    <p><b>Disease:</b> {disease}</p>
    <p><b>Risk Score:</b> {risk}%</p>
    <p><b>Alert Level:</b> {level}</p>
    <hr>
    <p><i>Immediate medical evaluation required.</i></p>
    """
    return send_real_email(subject, body, is_html=True)

def simulate_sms(patient_id, disease, risk, level):
    """Simulate sending an SMS to emergency response teams."""
    message = f"""
-----------------------------------------
[SMS SENT]
ALERT: Patient {patient_id} has critical {disease} risk ({risk}%). Immediate medical intervention required.
-----------------------------------------
"""
    print(message)
    return "SMS"

def detect_rapid_trend(patient_id, disease_type, current_risk, user_id=None):
    """
    Check if the risk has increased rapidly compared to previous assessments.
    Returns True if rapid escalation detected.
    """
    conn = get_db_connection()
    # Fetch last 2 records to calculate velocity
    col_map = {
        'Sepsis': 'sepsis_risk',
        'Heart Failure': 'heart_failure_risk',
        'Kidney Failure': 'kidney_failure_risk',
        'Pneumonia': 'pneumonia_risk'
    }
    
    col_name = col_map.get(disease_type)
    if not col_name:
        conn.close()
        return False, 0
        
    if user_id:
        history = conn.execute(f"SELECT {col_name} FROM disease_predictions WHERE patient_id = ? AND user_id = ? ORDER BY timestamp DESC LIMIT 2", (patient_id, user_id)).fetchall()
    else:
        history = conn.execute(f"SELECT {col_name} FROM disease_predictions WHERE patient_id = ? ORDER BY timestamp DESC LIMIT 2", (patient_id,)).fetchall()
    conn.close()
    
    if len(history) < 2:
        return False, 0
        
    latest_score = history[0][0]
    prev_score = history[1][0]
    
    # If the score jumped by more than 15% between adjacent readings
    if (latest_score - prev_score) >= 15.0:
        return True, prev_score
        
    return False, prev_score

def process_predictions(patient_id, patient_uid, current_risks, user_id=None):
    """
    Main hook to process multi-disease risk scores and evaluate Smart Alerts.
    current_risks: dict mapping disease name to integer/float risk
    e.g. {'Sepsis': 85.0, 'Heart Failure': 30.0, ...}
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    generated_alerts = []
    
    for disease, risk in current_risks.items():
        alert_level = None
        notification_types = ["Dashboard"]
        alert_message = ""
        
        email_status = "Not Sent"
        
        # 1. Advanced Trend Detection
        # Check if the disease risk rapidly spiked
        is_rapid, prev_score = detect_rapid_trend(patient_id, disease, risk, user_id=user_id)
        
        if is_rapid:
            alert_level = "Early Warning"
            alert_message = f"⚠ Rapid Risk Increase Detected: Risk increased from {prev_score}% to {risk}% rapidly. Immediate monitoring recommended."
            notification_types.append("Email") # Escalate early warnings to Email automatically
            email_status = simulate_email(patient_uid, disease, risk, alert_level)
            
        else:
            # 2. Threshold Evaluation (if not overridden by rapid trend)
            if risk > 90.0:
                alert_level = "Critical Emergency"
                alert_message = f"Immediate Life-Threatening Condition: {disease} risk is critical at {risk}%."
                notification_types.extend(["Email", "SMS"])
                email_status = simulate_email(patient_uid, disease, risk, alert_level)
                simulate_sms(patient_uid, disease, risk, alert_level)
                
            elif risk > 80.0:
                alert_level = "High Risk"
                alert_message = f"High Risk Alert: {disease} risk is elevated at {risk}%. Medical review required."
                notification_types.append("Email")
                email_status = simulate_email(patient_uid, disease, risk, alert_level)
                
            elif risk > 60.0:
                alert_level = "Warning"
                alert_message = f"Warning Alert: {disease} risk is {risk}%. Continue monitoring."
                # Dashboard only
                
            else:
                # Normal Monitoring, do nothing for this disease
                continue
                
        # Consolidate Notification types string (e.g. "Dashboard, Email")
        notif_str = ", ".join(notification_types)
        
        # Log to Database
        cursor.execute('''
        INSERT INTO smart_alert_logs 
        (patient_id, user_id, disease_type, risk_score, alert_level, alert_message, notification_type, email_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (patient_id, user_id, disease, risk, alert_level, alert_message, notif_str, email_status))
        
        generated_alerts.append({
            "disease": disease,
            "risk": risk,
            "level": alert_level,
            "notifications": notif_str,
            "email": email_status
        })
        
    conn.commit()
    conn.close()
    
    return generated_alerts

def get_recent_smart_alerts(limit=50, user_id=None):
    """
    Fetches historical alerts for the frontend Dashboard Smart Alert panel.
    """
    conn = get_db_connection()
    if user_id:
        query = '''
        SELECT s.*, p.patient_uid 
        FROM smart_alert_logs s
        JOIN patients p ON s.patient_id = p.id
        WHERE p.user_id = ?
        ORDER BY s.timestamp DESC
        LIMIT ?
        '''
        alerts = conn.execute(query, (user_id, limit)).fetchall()
    else:
        query = '''
        SELECT s.*, p.patient_uid 
        FROM smart_alert_logs s
        JOIN patients p ON s.patient_id = p.id
        ORDER BY s.timestamp DESC
        LIMIT ?
        '''
        alerts = conn.execute(query, (limit,)).fetchall()
    conn.close()
    return [dict(a) for a in alerts]

def check_alert_escalations():
    """
    Background worker function to check for alerts older than 2 minutes
    that have not been acknowledged. Simulating a hospital queue.
    """
    while True:
        try:
            conn = get_db_connection()
            # Find alerts older than 2 minutes that are not escalated and not acknowledged
            two_mins_ago = (datetime.utcnow() - timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:%S')
            
            query = '''
            SELECT s.*, p.patient_uid 
            FROM smart_alert_logs s
            JOIN patients p ON s.patient_id = p.id
            WHERE s.timestamp <= ? 
            AND s.escalated = 0 
            AND s.acknowledged = 0
            '''
            
            stale_alerts = conn.execute(query, (two_mins_ago,)).fetchall()
            
            for alert in stale_alerts:
                print(f"\n⚠ ALERT ESCALATION")
                print(f"Patient ID: {alert['patient_uid']}")
                print(f"Risk Score: {alert['risk_score']}%")
                print("No response detected. Escalating alert to ICU team.\n")
                
                # Update DB
                conn.execute('UPDATE smart_alert_logs SET escalated = 1 WHERE id = ?', (alert['id'],))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Escalation Error: {e}")
            
        time.sleep(10) # check every 10 seconds
