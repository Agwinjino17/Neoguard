import sqlite3
import os
import random
from datetime import datetime, timedelta

DB_PATH = 'neoguard.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def generate_mock_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if patient exists
    uid = "NEO-2026-001"
    cursor.execute('SELECT id FROM patients WHERE patient_uid = ?', (uid,))
    patient = cursor.fetchone()
    
    if not patient:
        cursor.execute('INSERT INTO patients (patient_uid, name, age_hours, weight_grams) VALUES (?, ?, ?, ?)', 
                       (uid, "Baby Doe", 48, 2500))
        patient_id = cursor.lastrowid
    else:
        patient_id = patient['id']
    
    # Generate 10 logs over the last 24 hours
    now = datetime.now()
    
    # Base clinical values
    base_hr = 140
    base_o2 = 97
    base_temp = 37.0
    
    for i in range(12):
        # Create a trend: Risk increases over time for mock visualization
        timestamp = now - timedelta(hours=(12-i)*2)
        
        # Add some noise and subtle trend
        hr = base_hr + (i * 3) + random.uniform(-5, 5)
        o2 = base_o2 - (i * 0.5) + random.uniform(-1, 1)
        temp = base_temp + (i * 0.1) + random.uniform(-0.2, 0.2)
        sbp = 60 + random.uniform(-5, 5)
        map_val = 45 + random.uniform(-3, 3)
        dbp = 35 + random.uniform(-4, 4)
        resp = 45 + (i * 2) + random.uniform(-5, 5)
        wbc = 10 + (i * 0.5)
        lactate = 1.0 + (i * 0.2)
        
        # Higher score as we "deteriorate" in this mock data
        score = min(0.1 + (i * 0.08), 0.95)
        label = "High Risk" if score > 0.5 else "Low Risk"
        
        cursor.execute('''
            INSERT INTO vital_logs (patient_id, hr, o2sat, temp, sbp, map, dbp, resp, wbc, lactate, prediction_score, prediction_label, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (patient_id, hr, o2, temp, sbp, map_val, dbp, resp, wbc, lactate, score, label, timestamp.strftime('%Y-%m-%d %H:%M:%S')))
        
    conn.commit()
    conn.close()
    print(f"Successfully generated 12 mock logs for {uid}")

if __name__ == '__main__':
    generate_mock_data()
