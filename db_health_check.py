import sqlite3
import os

db_path = 'neoguard.db'

def check_health():
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    tables = [
        'users', 'patients', 'vital_logs', 'treatment_logs', 
        'disease_predictions', 'advanced_alert_logs', 'smart_alert_logs',
        'icu_resource_predictions', 'patient_predictions', 'epidemic_alerts'
    ]

    print("--- Database Health Report ---")
    for table in tables:
        try:
            count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"Table: {table: <25} | Records: {count}")
            
            # Check for null user_id in sensitive tables
            if table not in ['users']:
                null_users = cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id IS NULL").fetchone()[0]
                if null_users > 0:
                    print(f"  [!] WARNING: {null_users} records with NULL user_id found.")
            
            # Check for orphaned patient records
            if table in ['vital_logs', 'treatment_logs', 'disease_predictions', 'advanced_alert_logs', 'smart_alert_logs', 'patient_predictions']:
                orphans = cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE patient_id NOT IN (SELECT id FROM patients)").fetchone()[0]
                if orphans > 0:
                    print(f"  [!] WARNING: {orphans} orphaned records found (patient_id not in patients table).")

        except Exception as e:
            print(f"  [!] Error checking {table}: {e}")

    print("\n--- Summary of Multi-tenant Integrity ---")
    try:
        user_counts = cursor.execute("SELECT u.name, COUNT(p.id) as p_count FROM users u LEFT JOIN patients p ON u.id = p.user_id GROUP BY u.id").fetchall()
        for row in user_counts:
            print(f"User: {row['name']: <20} | Patients Owned: {row['p_count']}")
    except Exception as e:
        print(f"  [!] Error checking user relationships: {e}")

    conn.close()

if __name__ == "__main__":
    check_health()
