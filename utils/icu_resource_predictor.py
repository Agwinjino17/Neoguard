import sqlite3
import uuid
from datetime import datetime, timedelta
from utils.database import get_db_connection

def analyze_icu_demand(scenario="Current", user_id=None):
    """
    Analyzes high-risk patient predictions over the last 24 hours to estimate ICU Resource Requirements.
    """
    conn = get_db_connection()
    
    # Analyze patients with critical disease risk scores (e.g. sepsis > 80%) in the last 24H
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    
    if user_id:
        query = '''
        SELECT COUNT(DISTINCT d.patient_id) as critical_count
        FROM disease_predictions d
        JOIN patients p ON d.patient_id = p.id
        WHERE (d.sepsis_risk > 80.0 OR d.heart_failure_risk > 80.0 OR d.kidney_failure_risk > 80.0 OR d.pneumonia_risk > 80.0)
        AND d.timestamp >= ? AND p.user_id = ?
        '''
        result = conn.execute(query, (yesterday, user_id)).fetchone()
    else:
        # We just want unique patients who hit > 80% risk for any disease
        query = '''
        SELECT COUNT(DISTINCT patient_id) as critical_count
        FROM disease_predictions
        WHERE (sepsis_risk > 80.0 OR heart_failure_risk > 80.0 OR kidney_failure_risk > 80.0 OR pneumonia_risk > 80.0)
        AND timestamp >= ?
        '''
        result = conn.execute(query, (yesterday,)).fetchone()
    base_critical_patients = result['critical_count'] if result else 0
    
    # Apply scenario multipliers
    if scenario == "Severe Outbreak":
        expected_critical_patients = base_critical_patients * 2
        if expected_critical_patients == 0:
            expected_critical_patients = 10 # Baseline floor for simulation
    else:
        expected_critical_patients = base_critical_patients
        
    # Heuristics Definition
    # Assume 70% of high-risk patients require ICU admission
    icu_admission_rate = 0.70
    expected_icu_patients = int(expected_critical_patients * icu_admission_rate)
    
    # 1 Bed per ICU patient
    icu_beds_required = expected_icu_patients
    
    # Assume 50% of ICU patients require ventilators
    ventilator_rate = 0.50
    ventilators_required = int(expected_icu_patients * ventilator_rate)
    
    # Assume 1 staff member needed per 2.5 ICU beds
    staff_required = int(icu_beds_required / 2.5) + 1
    
    # Define Hospital Capacity Limits (Hardcoded thresholds for demonstration)
    MAX_ICU_BEDS = 12
    MAX_VENTILATORS = 8
    
    # Determine Resource Status
    resource_status = "Sufficient"
    if icu_beds_required > MAX_ICU_BEDS or ventilators_required > MAX_VENTILATORS:
        resource_status = "Resource Shortage Risk"
    elif icu_beds_required >= (MAX_ICU_BEDS * 0.75):
        resource_status = "Moderate Demand"
        
    prediction_id = str(uuid.uuid4())
    
    # Log forecasting to database
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO icu_resource_predictions 
        (prediction_id, user_id, expected_sepsis_patients, expected_icu_patients, icu_beds_required, ventilators_required, staff_required, resource_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (prediction_id, user_id, expected_critical_patients, expected_icu_patients, icu_beds_required, ventilators_required, staff_required, resource_status))
    
    conn.commit()
    conn.close()
    
    data_source_description = "Forecast derived from patients hitting >80% critical risk for any disease (Sepsis, Heart Failure, Kidney Failure, Pneumonia) in the trailing 24 hours."
    
    return {
        "prediction_id": prediction_id,
        "scenario": scenario,
        "expected_sepsis_patients": expected_critical_patients, # Kept for schema backwards compatibility
        "expected_critical_patients": expected_critical_patients,
        "icu_beds_required": icu_beds_required,
        "ventilators_required": ventilators_required,
        "staff_required": staff_required,
        "resource_status": resource_status,
        "max_beds": MAX_ICU_BEDS,
        "data_source_description": data_source_description
    }

def analyze_historical_trends(user_id=None):
    """
    Analyzes prediction data over the last 3 days to determine growth trends.
    """
    conn = get_db_connection()
    
    now = datetime.utcnow()
    day1 = (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    day2 = (now - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
    day3 = (now - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
    
    def get_count_for_interval(start, end):
        if user_id:
            query = '''
            SELECT COUNT(DISTINCT d.patient_id) as count
            FROM disease_predictions d
            JOIN patients p ON d.patient_id = p.id
            WHERE (d.sepsis_risk > 80.0 OR d.heart_failure_risk > 80.0 OR d.kidney_failure_risk > 80.0 OR d.pneumonia_risk > 80.0)
            AND d.timestamp BETWEEN ? AND ? AND p.user_id = ?
            '''
            res = conn.execute(query, (start, end, user_id)).fetchone()
        else:
            query = '''
            SELECT COUNT(DISTINCT patient_id) as count
            FROM disease_predictions
            WHERE (sepsis_risk > 80.0 OR heart_failure_risk > 80.0 OR kidney_failure_risk > 80.0 OR pneumonia_risk > 80.0)
            AND timestamp BETWEEN ? AND ?
            '''
            res = conn.execute(query, (start, end)).fetchone()
        return res['count'] if res else 0

    d1_count = get_count_for_interval(day1, now.strftime('%Y-%m-%d %H:%M:%S'))
    d2_count = get_count_for_interval(day2, day1)
    d3_count = get_count_for_interval(day3, day2)
    
    conn.close()
    
    trend = "Stable"
    if d1_count > d2_count and d2_count >= d3_count and d1_count > 0:
        trend = "Increasing"
    elif d1_count < d2_count and d2_count <= d3_count:
        trend = "Decreasing"
        
    return trend
