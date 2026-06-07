import sqlite3
import json
import random
from datetime import datetime, timedelta
from utils.database import get_db_connection
from utils.mailer import send_real_email

def trigger_outbreak_notification(disease, today, yesterday, ward):
    """
    Sends an emergency outbreak email to the Infection Control Team.
    """
    subject = f"CRITICAL: Outbreak Detected - {disease} in {ward}"
    body = f"""
    <h2>[WARNING] POSSIBLE INFECTION CLUSTER DETECTED</h2>
    <p><b>Disease:</b> {disease}</p>
    <p><b>Location:</b> {ward}</p>
    <p><b>Today's Cases:</b> {today}</p>
    <p><b>Yesterday's Cases:</b> {yesterday}</p>
    <hr>
    <p><b>Action:</b> Deploy Infection Control Team immediately.</p>
    """
    return send_real_email(subject, body, is_html=True)

def analyze_ward_risks(user_id=None):
    """
    Maps the current critical infection probability per ward based on recent disease predictions.
    """
    conn = get_db_connection()
    now = datetime.utcnow()
    last_week = (now - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    
    # Get active case count grouped by ward
    if user_id:
        query = '''
            SELECT p.ward, COUNT(dp.id) as case_count 
            FROM disease_predictions dp
            JOIN patients p ON dp.patient_id = p.id
            WHERE (dp.sepsis_risk > 80.0 OR dp.pneumonia_risk > 80.0)
            AND dp.timestamp >= ? AND p.user_id = ?
            GROUP BY p.ward
        '''
        ward_counts = conn.execute(query, (last_week, user_id)).fetchall()
    else:
        query = '''
            SELECT p.ward, COUNT(dp.id) as case_count 
            FROM disease_predictions dp
            JOIN patients p ON dp.patient_id = p.id
            WHERE dp.sepsis_risk > 80.0 OR dp.pneumonia_risk > 80.0
            AND dp.timestamp >= ?
            GROUP BY p.ward
        '''
        ward_counts = conn.execute(query, (last_week,)).fetchall()
        
    conn.close()
    
    ward_risks = []
    for row in ward_counts:
        count = row['case_count']
        ward = row['ward']
        if count >= 10:
            risk = "High"
        elif count >= 4:
            risk = "Moderate"
        else:
            risk = "Low"
            
        ward_risks.append({
            "ward": ward,
            "cases": count,
            "risk_level": risk
        })
        
    # Ensure some defaults if database is empty
    known_wards = [w['ward'] for w in ward_risks]
    for default_ward in ["Ward A", "Ward B", "ICU", "General Ward"]:
        if default_ward not in known_wards:
            ward_risks.append({"ward": default_ward, "cases": 0, "risk_level": "Low"})
            
    # Sort by cases descending
    ward_risks = sorted(ward_risks, key=lambda x: x['cases'], reverse=True)
    return ward_risks

def analyze_epidemic_trends(user_id=None):
    """
    Analyzes all predictions over the last 7 days. Extracts timeline data 
    and checks if an outbreak threshold (>2x spike) was crossed today.
    """
    conn = get_db_connection()
    now = datetime.utcnow()
    
    trend_data = {
        "dates": [],
        "sepsis": [],
        "pneumonia": [],
        "kidney_failure": [],
        "heart_failure": []
    }
    
    daily_stats = {}
    
    # Gather 7 days backwards
    for i in range(6, -1, -1):
        target_date = (now - timedelta(days=i)).strftime('%Y-%m-%d')
        start = f"{target_date} 00:00:00"
        end = f"{target_date} 23:59:59"
        
        if user_id:
            query = '''
                SELECT 
                    SUM(CASE WHEN dp.sepsis_risk > 80.0 THEN 1 ELSE 0 END) as sepsis_cases,
                    SUM(CASE WHEN dp.pneumonia_risk > 80.0 THEN 1 ELSE 0 END) as pneumonia_cases,
                    SUM(CASE WHEN dp.kidney_failure_risk > 80.0 THEN 1 ELSE 0 END) as kidney_cases,
                    SUM(CASE WHEN dp.heart_failure_risk > 80.0 THEN 1 ELSE 0 END) as heart_cases
                FROM disease_predictions dp
                JOIN patients p ON dp.patient_id = p.id
                WHERE dp.timestamp BETWEEN ? AND ? AND p.user_id = ?
            '''
            res = conn.execute(query, (start, end, user_id)).fetchone()
        else:
            query = '''
                SELECT 
                    SUM(CASE WHEN sepsis_risk > 80.0 THEN 1 ELSE 0 END) as sepsis_cases,
                    SUM(CASE WHEN pneumonia_risk > 80.0 THEN 1 ELSE 0 END) as pneumonia_cases,
                    SUM(CASE WHEN kidney_failure_risk > 80.0 THEN 1 ELSE 0 END) as kidney_cases,
                    SUM(CASE WHEN heart_failure_risk > 80.0 THEN 1 ELSE 0 END) as heart_cases
                FROM disease_predictions
                WHERE timestamp BETWEEN ? AND ?
            '''
            res = conn.execute(query, (start, end)).fetchone()
        
        d_sepsis = res['sepsis_cases'] or 0
        d_pneu = res['pneumonia_cases'] or 0
        d_kidn = res['kidney_cases'] or 0
        d_heart = res['heart_cases'] or 0
        
        trend_data["dates"].append(target_date)
        trend_data["sepsis"].append(d_sepsis)
        trend_data["pneumonia"].append(d_pneu)
        trend_data["kidney_failure"].append(d_kidn)
        trend_data["heart_failure"].append(d_heart)
        
        label = "today" if i == 0 else "yesterday" if i == 1 else f"day_{i}"
        daily_stats[label] = {
            "Sepsis": d_sepsis,
            "Pneumonia": d_pneu,
            "Kidney Failure": d_kidn,
            "Heart Failure": d_heart
        }

    # Spike Algorithm Analysis (Today vs Yesterday)
    # Rule: > 2x increase AND Today's cases >= 3 (to avoid noise like 0->1 jumping)
    outbreaks_detected = []
    
    if "today" in daily_stats and "yesterday" in daily_stats:
        for disease in ["Sepsis", "Pneumonia", "Kidney Failure", "Heart Failure"]:
            today_cases = daily_stats["today"][disease]
            yesterday_cases = daily_stats["yesterday"][disease]
            
            # Ensure base multiplier math doesn't div by zero; 1 case yesterday mapping to 3 today = spike
            comparator = yesterday_cases if yesterday_cases > 0 else 1
            
            if today_cases > (comparator * 2) and today_cases >= 3:
                # Outbreak detected!
                
                # Identify worst ward for this disease
                start_today = f"{now.strftime('%Y-%m-%d')} 00:00:00"
                col_name = disease.lower().replace(" ", "_") + "_risk"
                
                if user_id:
                    ward_query = f'''
                        SELECT p.ward, COUNT(dp.id) as case_count 
                        FROM disease_predictions dp
                        JOIN patients p ON dp.patient_id = p.id
                        WHERE dp.{col_name} > 80.0 AND dp.timestamp >= ? AND p.user_id = ?
                        GROUP BY p.ward ORDER BY case_count DESC LIMIT 1
                    '''
                    worst_ward_row = conn.execute(ward_query, (start_today, user_id)).fetchone()
                else:
                    ward_query = f'''
                        SELECT p.ward, COUNT(dp.id) as case_count 
                        FROM disease_predictions dp
                        JOIN patients p ON dp.patient_id = p.id
                        WHERE dp.{col_name} > 80.0 AND dp.timestamp >= ?
                        GROUP BY p.ward ORDER BY case_count DESC LIMIT 1
                    '''
                    worst_ward_row = conn.execute(ward_query, (start_today,)).fetchone()
                    
                target_ward = worst_ward_row['ward'] if worst_ward_row else "Unknown Location"
                
                # Check if we already alerted this exact combo today to avoid spamming
                check_query = '''SELECT id FROM epidemic_alerts WHERE disease_type = ? AND target_ward = ? AND timestamp >= ?'''
                existing = conn.execute(check_query, (disease, target_ward, start_today)).fetchone()
                
                if not existing:
                    # Log the outbreak
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO epidemic_alerts (user_id, disease_type, today_cases, yesterday_cases, target_ward, notification_status)
                        VALUES (?, ?, ?, ?, ?, 'Sent Email')
                    ''', (user_id, disease, today_cases, yesterday_cases, target_ward))
                    conn.commit()
                    
                    trigger_outbreak_notification(disease, today_cases, yesterday_cases, target_ward)
                    
                outbreaks_detected.append({
                    "disease": disease,
                    "target_ward": target_ward,
                    "today": today_cases,
                    "yesterday": yesterday_cases
                })
                
    # Fetch recent active alerts for UI
    active_alerts = conn.execute('SELECT * FROM epidemic_alerts ORDER BY timestamp DESC LIMIT 5').fetchall()
    
    conn.close()
    
    return {
        "trend_chart": trend_data,
        "ward_risks": analyze_ward_risks(user_id=user_id),
        "recent_alerts": [dict(a) for a in active_alerts]
    }

def simulate_epidemic_data(user_id):
    """
    Procedurally generates mock patients and disease predictions spanning 7 days to simulate a Sepsis 
    outbreak occurring TODAY in Ward B. Safe to run repeatedly.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow()
    
    # Clear out old fake demo patients to avoid runaway inflation
    cursor.execute("DELETE FROM patients WHERE name LIKE 'SimPatient_%'")
    cursor.execute("DELETE FROM disease_predictions WHERE patient_id NOT IN (SELECT id FROM patients)")
    cursor.execute("DELETE FROM epidemic_alerts")
    conn.commit()
    
    wards = ["Ward A", "ICU", "General Ward", "Pediatrics"]
    
    # Inject baseline cases 7 days back
    for i in range(6, 0, -1):
        target_date = (now - timedelta(days=i)).replace(hour=12)
        
        # 1-2 random sepsis cases a day
        num_cases = random.randint(1, 2)
        for _ in range(num_cases):
            cursor.execute("INSERT INTO patients (patient_uid, name, ward, created_at, user_id) VALUES (?, ?, ?, ?, ?)",
                            (f"SIM-{i}-{random.randint(100,999)}", f"SimPatient_{i}", random.choice(wards), target_date, user_id))
            pid = cursor.lastrowid
            
            cursor.execute('''INSERT INTO disease_predictions 
                            (patient_id, sepsis_risk, heart_failure_risk, kidney_failure_risk, pneumonia_risk, timestamp, user_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                            (pid, 85.0, 10.0, 10.0, 20.0, target_date, user_id))
            
    # Inject the OUTBREAK TODAY (Day 0) in Ward B
    today_date = now.replace(hour=14)
    outbreak_cases = 11
    
    for _ in range(outbreak_cases):
         cursor.execute("INSERT INTO patients (patient_uid, name, ward, created_at, user_id) VALUES (?, ?, ?, ?, ?)",
                            (f"SIM-0-{random.randint(1000,9999)}", "SimPatient_Today", "Ward B", today_date, user_id))
         pid = cursor.lastrowid
         
         cursor.execute('''INSERT INTO disease_predictions 
                            (patient_id, sepsis_risk, heart_failure_risk, kidney_failure_risk, pneumonia_risk, timestamp, user_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                            (pid, 95.0, 15.0, 5.0, 10.0, today_date, user_id))
                            
    # Throw in some random pneumonia
    for _ in range(3):
        cursor.execute("INSERT INTO patients (patient_uid, name, ward, created_at, user_id) VALUES (?, ?, ?, ?, ?)",
                            (f"SIM-P-{random.randint(1000,9999)}", "SimPatient_Pneu", "General Ward", today_date, user_id))
        pid = cursor.lastrowid
        cursor.execute('''INSERT INTO disease_predictions 
                            (patient_id, sepsis_risk, heart_failure_risk, kidney_failure_risk, pneumonia_risk, timestamp, user_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                            (pid, 10.0, 10.0, 10.0, 92.0, today_date, user_id))

    conn.commit()
    conn.close()
    
    # Run the engine to detect the freshly simulated outbreak
    return analyze_epidemic_trends(user_id=user_id)
