import json
import os
import sqlite3
from datetime import datetime, timedelta
from utils.database import get_db_connection

# Load Staff Directory
STAFF_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'staff_directory.json')
STAFF_DIRECTORY = {}
if os.path.exists(STAFF_CONFIG_PATH):
    with open(STAFF_CONFIG_PATH, 'r') as f:
        STAFF_DIRECTORY = json.load(f)

def determine_level_and_action(risk_score):
    """
    Returns (Level Name, Priority, Assigned Role)
    """
    if risk_score >= 95.0:
        return "ICU Emergency", 1, STAFF_DIRECTORY.get("icu_team", "ICU Team")
    elif risk_score >= 85.0:
        return "Critical", 2, STAFF_DIRECTORY.get("doctor_on_call", "Doctor")
    elif risk_score >= 70.0:
        return "Warning", 3, STAFF_DIRECTORY.get("nurse_station", "Nurse Station")
    else:
        return "Monitor", 4, None

def calculate_trend(patient_id, disease, current_score, user_id=None):
    """
    Analyzes historical risk scores to determine trend and predictive escalation.
    Returns (Trend Status, Predictive Risk Score)
    """
    conn = get_db_connection()
    # Fetch last 3 records for this disease
    col_name = f"{disease.lower().replace(' ', '_')}_risk"
    
    # Ensure column exists in our logic, if not we fall back
    if col_name not in ['sepsis_risk', 'heart_failure_risk', 'kidney_failure_risk', 'pneumonia_risk']:
        conn.close()
        return "Stable", current_score

    if user_id:
        query = f"SELECT {col_name}, timestamp FROM disease_predictions WHERE patient_id = ? AND user_id = ? ORDER BY timestamp DESC LIMIT 3"
        history = conn.execute(query, (patient_id, user_id)).fetchall()
    else:
        query = f"SELECT {col_name}, timestamp FROM disease_predictions WHERE patient_id = ? ORDER BY timestamp DESC LIMIT 3"
        history = conn.execute(query, (patient_id,)).fetchall()
    conn.close()

    if len(history) < 2:
        return "Stable", current_score

    # Calculate velocity (rate of change)
    latest_score = history[0][0]
    prev_score = history[1][0]
    
    delta = latest_score - prev_score
    
    if delta > 10.0:
        trend = "Rapidly Escalating"
        # Predict next 3 hours (naive extrapolation: assume another jump)
        predicted_risk = min(100.0, current_score + (delta * 2))
    elif delta > 3.0:
        trend = "Increasing"
        predicted_risk = min(100.0, current_score + delta)
    elif delta < -3.0:
        trend = "Decreasing"
        predicted_risk = max(0.0, current_score + delta)
    else:
        trend = "Stable"
        predicted_risk = current_score

    return trend, predicted_risk

def evaluate_patient_alerts(patient_id, current_risks, user_id=None):
    """
    Entry point after a new prediction is made.
    current_risks: dict like {'sepsis_risk': 80.5, 'heart_failure_risk': 40.0, ...}
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    alerts_generated = []

    disease_map = {
        'Sepsis': 'sepsis_risk',
        'Heart Failure': 'heart_failure_risk',
        'Kidney Failure': 'kidney_failure_risk',
        'Pneumonia': 'pneumonia_risk'
    }

    for disease_name, key in disease_map.items():
        if key not in current_risks:
            continue
            
        current_score = current_risks[key]
        trend, predicted_risk = calculate_trend(patient_id, disease_name, current_score, user_id=user_id)
        
        # Primary Alert Logic
        level, priority, assigned_staff = determine_level_and_action(current_score)
        
        # Predictive Override Logic
        # If current is Monitor but predicted is Critical/Emergency, trigger early warning
        if priority == 4 and predicted_risk >= 85.0:
            level = "Predictive Warning"
            priority = 3
            assigned_staff = STAFF_DIRECTORY.get("doctor_on_call", "Doctor")
            trend = "Rapidly Escalating (Predicted Critical)"

        # Save active alert to DB if priority < 4
        if priority < 4:
            cursor.execute('''
                INSERT INTO advanced_alert_logs 
                (patient_id, user_id, disease_type, risk_score, alert_level, alert_priority, trend_status, assigned_staff)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (patient_id, user_id, disease_name, current_score, level, priority, trend, assigned_staff))
            
            alerts_generated.append({
                "disease": disease_name,
                "level": level,
                "priority": priority,
                "staff": assigned_staff
            })

    conn.commit()
    conn.close()
    
    return alerts_generated

def get_active_alerts(user_id=None):
    """
    Fetches all unacknowledged alerts sorted by priority (1=Highest).
    """
    conn = get_db_connection()
    if user_id:
        query = '''
            SELECT a.*, p.patient_uid 
            FROM advanced_alert_logs a
            JOIN patients p ON a.patient_id = p.id
            WHERE a.acknowledged_by IS NULL AND p.user_id = ?
            ORDER BY a.alert_priority ASC, a.timestamp DESC
        '''
        alerts = conn.execute(query, (user_id,)).fetchall()
    else:
        query = '''
            SELECT a.*, p.patient_uid 
            FROM advanced_alert_logs a
            JOIN patients p ON a.patient_id = p.id
            WHERE a.acknowledged_by IS NULL
            ORDER BY a.alert_priority ASC, a.timestamp DESC
        '''
        alerts = conn.execute(query).fetchall()
    conn.close()
    return [dict(row) for row in alerts]

def acknowledge_alert(alert_id, staff_name, user_id=None):
    """
    Marks all active alerts for the patient associated with `alert_id` as acknowledged.
    Verifies that the alert belongs to the requesting user if user_id is provided.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Identify the patient_id of the alert being cleared
    if user_id:
        alert = cursor.execute("SELECT patient_id FROM advanced_alert_logs WHERE id = ? AND user_id = ?", (alert_id, user_id)).fetchone()
    else:
        alert = cursor.execute("SELECT patient_id FROM advanced_alert_logs WHERE id = ?", (alert_id,)).fetchone()
    
    if alert:
        # Acknowledge all unacknowledged alerts for this patient
        if user_id:
            cursor.execute('''
                UPDATE advanced_alert_logs
                SET acknowledged_by = ?
                WHERE patient_id = ? AND user_id = ? AND acknowledged_by IS NULL
            ''', (staff_name, alert['patient_id'], user_id))
        else:
            cursor.execute('''
                UPDATE advanced_alert_logs
                SET acknowledged_by = ?
                WHERE patient_id = ? AND acknowledged_by IS NULL
            ''', (staff_name, alert['patient_id']))
        
    conn.commit()
    conn.close()
    return True

def get_alert_analytics(user_id=None):
    """
    Returns analytics for the dashboard.
    """
    conn = get_db_connection()
    
    if user_id:
        total = conn.execute("SELECT COUNT(*) FROM advanced_alert_logs a JOIN patients p ON a.patient_id = p.id WHERE p.user_id = ?", (user_id,)).fetchone()[0]
        critical = conn.execute("SELECT COUNT(*) FROM advanced_alert_logs a JOIN patients p ON a.patient_id = p.id WHERE a.alert_priority <= 2 AND p.user_id = ?", (user_id,)).fetchone()[0]
        icu = conn.execute("SELECT COUNT(*) FROM advanced_alert_logs a JOIN patients p ON a.patient_id = p.id WHERE a.alert_priority = 1 AND p.user_id = ?", (user_id,)).fetchone()[0]
    else:
        # Total alerts
        total = conn.execute("SELECT COUNT(*) FROM advanced_alert_logs").fetchone()[0]
        
        # Critical and Emergency
        critical = conn.execute("SELECT COUNT(*) FROM advanced_alert_logs WHERE alert_priority <= 2").fetchone()[0]
        
        # ICU Emergencies
        icu = conn.execute("SELECT COUNT(*) FROM advanced_alert_logs WHERE alert_priority = 1").fetchone()[0]
        
    conn.close()
    
    return {
        "total_alerts": total,
        "critical_alerts": critical,
        "icu_emergencies": icu
    }
