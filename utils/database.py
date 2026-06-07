import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

DB_PATH = 'neoguard.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Patients table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_uid TEXT NOT NULL,
        name TEXT,
        age_hours INTEGER,
        weight_grams INTEGER,
        ward TEXT DEFAULT 'General Ward',
        user_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(patient_uid, user_id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    
    # Vital Logs (Time Series data)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vital_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        user_id INTEGER,
        hr REAL,
        o2sat REAL,
        temp REAL,
        sbp REAL,
        map REAL,
        dbp REAL,
        resp REAL,
        wbc REAL,
        lactate REAL,
        prediction_score REAL,
        prediction_label TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Treatment Logs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS treatment_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        risk_score REAL,
        risk_level TEXT,
        recommendations TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients (id)
    )
    ''')
    
    # Multi-disease predictions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS disease_predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        user_id INTEGER,
        sepsis_risk REAL,
        heart_failure_risk REAL,
        kidney_failure_risk REAL,
        pneumonia_risk REAL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Advanced Alert System Logs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS advanced_alert_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        user_id INTEGER,
        disease_type TEXT,
        risk_score REAL,
        alert_level TEXT,
        alert_priority INTEGER,
        trend_status TEXT,
        assigned_staff TEXT,
        acknowledged_by TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Smart Alert System Logs
    # Note: SQLite ALTER TABLE is limited, so for simplicity in this demo we use IF NOT EXISTS.
    # In a real environment we'd use migrations.
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS smart_alert_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        user_id INTEGER,
        disease_type TEXT,
        risk_score REAL,
        alert_level TEXT,
        alert_message TEXT,
        notification_type TEXT,
        email_status TEXT DEFAULT 'Not Sent',
        escalated BOOLEAN DEFAULT 0,
        acknowledged BOOLEAN DEFAULT 0,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # We will attempt to alter table to add columns if they don't exist gracefully
    try:
        cursor.execute("ALTER TABLE smart_alert_logs ADD COLUMN email_status TEXT DEFAULT 'Not Sent'")
        cursor.execute("ALTER TABLE smart_alert_logs ADD COLUMN escalated BOOLEAN DEFAULT 0")
        cursor.execute("ALTER TABLE smart_alert_logs ADD COLUMN acknowledged BOOLEAN DEFAULT 0")
    except Exception:
        pass # Columns already exist likely
    
    # ICU Resource Predictions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS icu_resource_predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prediction_id TEXT UNIQUE,
        user_id INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expected_sepsis_patients INTEGER,
        expected_icu_patients INTEGER,
        icu_beds_required INTEGER,
        ventilators_required INTEGER,
        staff_required INTEGER,
        resource_status TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    
    # Patient Risk Predictions (Flattened for Live Feed)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS patient_predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        patient_uid TEXT,
        user_id INTEGER,
        disease_type TEXT,
        risk_score REAL,
        alert_level TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Epidemic Alerts Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS epidemic_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        disease_type TEXT,
        today_cases INTEGER,
        yesterday_cases INTEGER,
        target_ward TEXT,
        notification_status TEXT DEFAULT 'Pending',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')

    # Schema Migrations for Session Isolation (Add user_id to all tables)
    migration_tables = [
        'patients', 'vital_logs', 'treatment_logs', 
        'disease_predictions', 'advanced_alert_logs', 'smart_alert_logs',
        'icu_resource_predictions', 'epidemic_alerts'
    ]
    for table in migration_tables:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES users(id)")
            print(f"[NeoGuard DB] Added user_id column to {table}")
        except Exception:
            pass # Column already exists

    # Fix Patients Table Constraint (Global UNIQUE -> Composite UNIQUE)
    # Check if the global unique constraint still exists by trying to insert a collision
    try:
        # We check the table info to see if patient_uid is marked as unique at a column level
        table_info = cursor.execute("PRAGMA table_info(patients)").fetchall()
        # Unfortunately PRAGMA table_info doesn't show constraints clearly enough easily
        # We'll use a safer approach: check the index list
        indexes = cursor.execute("PRAGMA index_list(patients)").fetchall()
        is_global_unique = False
        for idx in indexes:
            # If there's a unique index on JUST patient_uid
            idx_name = idx['name']
            idx_info = cursor.execute(f"PRAGMA index_info('{idx_name}')").fetchall()
            if idx['unique'] == 1 and len(idx_info) == 1 and idx_info[0]['name'] == 'patient_uid':
                is_global_unique = True
                break
        
        if is_global_unique:
            print("[NeoGuard DB] Fixing global UNIQUE constraint on patients...")
            # 1. Rename old table
            cursor.execute("ALTER TABLE patients RENAME TO patients_old")
            # 2. Create new table (definition above will be used if we just call init_db again, 
            # but for safety we define it here too or just use the current one)
            cursor.execute('''
            CREATE TABLE patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_uid TEXT NOT NULL,
                name TEXT,
                age_hours INTEGER,
                weight_grams INTEGER,
                ward TEXT DEFAULT 'General Ward',
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(patient_uid, user_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            ''')
            # 3. Copy data
            cursor.execute('''
                INSERT INTO patients (id, patient_uid, name, age_hours, weight_grams, ward, user_id, created_at)
                SELECT id, patient_uid, name, age_hours, weight_grams, ward, user_id, created_at FROM patients_old
            ''')
            # 4. Drop old table
            cursor.execute("DROP TABLE patients_old")
            print("[NeoGuard DB] Composite UNIQUE constraint enforced.")
    except Exception as e:
        print(f"[NeoGuard DB] Migration error (Constraint Fix): {e}")

    # Attempt to alter table patients to add ward column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE patients ADD COLUMN ward TEXT DEFAULT 'General Ward'")
    except Exception:
        pass

    # Users Table (Authentication) - MUST BE CREATED BEFORE DEPENDENT TABLES
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'staff',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Default Admin User Generation
    admin_exists = cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1").fetchone()
    if not admin_exists:
        try:
            default_password_hash = generate_password_hash("admin123")
            cursor.execute('''
                INSERT INTO users (name, email, password_hash, role)
                VALUES (?, ?, ?, ?)
            ''', ("System Admin", "admin@neoguard.hospital", default_password_hash, "admin"))
            print("[NeoGuard DB] Created default admin account (admin@neoguard.hospital / admin123)")
        except Exception as e:
            print(f"[NeoGuard DB] Could not create default admin: {e}")

    # Login Logs Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS login_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ip_address TEXT,
        status TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
