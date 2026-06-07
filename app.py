from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, session, redirect, url_for, flash
import os
import pandas as pd
import json
import uuid
import threading
from utils.predict import get_prediction, get_batch_predictions
from utils.train_model import train_model
from utils.database import get_db_connection, init_db
from utils.treatment_recommendation import get_treatment_recommendation
from utils.multi_disease_predictor import get_multi_prediction, train_multi_disease_models
from utils.voice_assistant import execute_voice_command, AUDIO_DIR
from utils.advanced_alert_engine import evaluate_patient_alerts, get_active_alerts, acknowledge_alert, get_alert_analytics
from utils.smart_alert_system import process_predictions, get_recent_smart_alerts, check_alert_escalations
from utils.icu_resource_predictor import analyze_icu_demand, analyze_historical_trends
from utils.epidemic_outbreak_engine import analyze_epidemic_trends, simulate_epidemic_data

app = Flask(__name__)
app.config['SECRET_KEY'] = 'neoguard_super_secret_clinical_key_2026' # In a real app, use os.environ.get('SECRET_KEY')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MODEL_PATH'] = os.path.join('model', 'model.pkl')
app.config['DATASET_PATH'] = os.path.join('dataset', 'sepsis_data.csv')
app.config['PERMANENT_SESSION_LIFETIME'] = 1800 # 30 minutes

# Ensure necessary directories exist
for folder in [app.config['UPLOAD_FOLDER'], 'model', 'dataset']:
    if not os.path.exists(folder):
        os.makedirs(folder)

from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_user():
    return dict(
        current_user_name=session.get('user_name'),
        current_user_role=session.get('user_role'),
        is_logged_in='user_id' in session
    )

def initialize_system():
    """Check for model existence and initialize DB."""
    init_db()
    if not os.path.exists(app.config['MODEL_PATH']):
        print("Pre-trained NeoGuard model not found. Retraining ensemble...")
        success, message = train_model()
        if not success:
            return False, f"Intelligence Module Error: {message}"
            
    # Also check multi-disease models
    if not os.path.exists(os.path.join('model', 'pneumonia_model.pkl')):
        print("Pre-trained multi-disease models not found. Retraining...")
        success, message = train_multi_disease_models()
        if not success:
            return False, f"Multi-Disease Module Error: {message}"
            
    return True, "NeoGuard System Ready."

# Initialize model on startup
system_ready, system_message = initialize_system()

@app.after_request
def add_header(response):
    """Enforce Data Privacy and Session Isolation by disabling browser caching."""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    """NeoGuard Secure Authentication."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        ip_addr = request.remote_addr

        if not email or not password:
            return render_template('login.html', error="All fields are required.")

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            # Success
            session.permanent = True
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            
            # Log success
            conn.execute('INSERT INTO login_logs (user_id, ip_address, status) VALUES (?, ?, ?)',
                         (user['id'], ip_addr, 'SUCCESS'))
            conn.commit()
            conn.close()
            return redirect(url_for('home'))
        else:
            # Failed
            if user:
                conn.execute('INSERT INTO login_logs (user_id, ip_address, status) VALUES (?, ?, ?)',
                             (user['id'], ip_addr, 'FAILED'))
                conn.commit()
            conn.close()
            return render_template('login.html', error="Invalid clinical credentials.")

    # Redirect if already logged in
    if 'user_id' in session:
        return redirect(url_for('home'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """NeoGuard Secure Staff Registration."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        role = request.form.get('role', 'staff')
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not name or not email or not password or not confirm_password:
            return render_template('register.html', error="All fields are required.")

        if password != confirm_password:
            return render_template('register.html', error="Passcodes do not match.")

        if len(password) < 8:
            return render_template('register.html', error="Passcode must be at least 8 characters long.")

        valid_roles = ['doctor', 'nurse', 'admin', 'staff']
        if role not in valid_roles:
            role = 'staff'

        conn = get_db_connection()
        existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        
        if existing_user:
            conn.close()
            return render_template('register.html', error="An account with this email already exists.")

        try:
            pwd_hash = generate_password_hash(password)
            conn.execute('''
                INSERT INTO users (name, email, password_hash, role)
                VALUES (?, ?, ?, ?)
            ''', (name, email, pwd_hash, role))
            conn.commit()
            conn.close()
            return render_template('login.html', success="Account created successfully. Please authenticate.")
        except Exception as e:
            conn.close()
            return render_template('register.html', error=f"Registration error: {str(e)}")

    # Redirect if already logged in
    if 'user_id' in session:
        return redirect(url_for('home'))

    return render_template('register.html')

@app.route('/')
@login_required
def home():
    """NeoGuard Clinical Entry."""
    return render_template('index.html', active_page='home', heading="Clinical Entry Portal")

@app.route('/dashboard')
@login_required
def dashboard():
    """Predictive Intelligence Dashboard."""
    return render_template('dashboard.html', active_page='dashboard', heading="Temporal Analytics")

@app.route('/patients')
@login_required
def patients():
    """Patient Monitoring Roster."""
    user_id = session.get('user_id')
    conn = get_db_connection()
    patients = conn.execute('SELECT * FROM patients WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
    conn.close()
    return render_template('patients.html', patients=patients, active_page='patients', heading="Central Records")

# ── Medical Reading Constraints ──────────────────────────────────────────────
MEDICAL_CONSTRAINTS = {
    'HR':      {'min': 20,   'max': 300,  'label': 'Heart Rate',       'unit': 'bpm'},
    'O2Sat':   {'min': 50,   'max': 100,  'label': 'O2 Saturation',    'unit': '%'},
    'Temp':    {'min': 25,   'max': 45,   'label': 'Temperature',      'unit': '°C'},
    'SBP':     {'min': 40,   'max': 300,  'label': 'Systolic BP',      'unit': 'mmHg'},
    'MAP':     {'min': 20,   'max': 200,  'label': 'Mean Arterial P.', 'unit': 'mmHg'},
    'DBP':     {'min': 20,   'max': 200,  'label': 'Diastolic BP',     'unit': 'mmHg'},
    'Resp':    {'min': 4,    'max': 60,   'label': 'Respiration Rate', 'unit': 'bpm'},
    'WBC':     {'min': 0.5,  'max': 500,  'label': 'WBC Count',        'unit': '×10⁹/L'},
    'Lactate': {'min': 0.1,  'max': 30,   'label': 'Lactate',          'unit': 'mmol/L'},
}

def validate_medical_data(data):
    """Validate all medical readings against clinical constraints.
    Returns (True, None) if valid, or (False, error_message) if not.
    """
    errors = []
    for field, c in MEDICAL_CONSTRAINTS.items():
        val = data.get(field)
        if val is None:
            errors.append(f"{c['label']} is required.")
            continue
        try:
            val = float(val)
        except (TypeError, ValueError):
            errors.append(f"{c['label']} must be a valid number.")
            continue
        if val < c['min'] or val > c['max']:
            errors.append(
                f"{c['label']} ({val} {c['unit']}) is out of range. "
                f"Valid range: {c['min']} – {c['max']} {c['unit']}."
            )
    if errors:
        return False, " | ".join(errors)
    return True, None

# ─────────────────────────────────────────────────────────────────────────────

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    """NeoGuard Intelligence Assessment Logic."""
    try:
        user_id = session.get('user_id')
        uid = request.form.get('patient_uid', '').strip()
        ward = request.form.get('ward', 'General Ward')

        # Validate Patient UID
        if not uid:
            return render_template('index.html', error="Patient UID is required.", active_page='home')

        # Parse numeric fields
        try:
            data = {
                'HR':      float(request.form.get('HR', '')),
                'O2Sat':   float(request.form.get('O2Sat', '')),
                'Temp':    float(request.form.get('Temp', '')),
                'SBP':     float(request.form.get('SBP', '')),
                'MAP':     float(request.form.get('MAP', '')),
                'DBP':     float(request.form.get('DBP', '')),
                'Resp':    float(request.form.get('Resp', '')),
                'WBC':     float(request.form.get('WBC', '')),
                'Lactate': float(request.form.get('Lactate', '')),
            }
        except ValueError as ve:
            return render_template('index.html',
                                   error=f"Invalid input: all medical readings must be numeric. ({ve})",
                                   active_page='home')

        # Server-side constraint validation
        is_valid, validation_error = validate_medical_data(data)
        if not is_valid:
            return render_template('index.html', error=f"Validation Error: {validation_error}", active_page='home')
        
        # Run prediction through ensemble (XGBoost + placeholders for CNN/LSTM)
        result = get_prediction(data)
        
        if "error" in result:
            return render_template('index.html', error=result["error"], active_page='home')
            
        # Run multi-disease predictions
        multi_result = get_multi_prediction(data)
        if "error" in multi_result:
             return render_template('index.html', error=multi_result["error"], active_page='home')
            
        # CDSS Treatment Recommendation Engine
        treatment_data = get_treatment_recommendation(result['probability'])
        result['treatment'] = treatment_data
            
        # Persistence Logic (Time Series Support)
        conn = get_db_connection()
        # 1. Get or create patient
        patient = conn.execute('SELECT id FROM patients WHERE patient_uid = ? AND user_id = ?', (uid, user_id)).fetchone()
        if not patient:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO patients (patient_uid, ward, user_id) VALUES (?, ?, ?)', (uid, ward, user_id))
            conn.commit()
            p_id = cursor.lastrowid
        else:
            p_id = patient['id']
            # Update ward if changed
            cursor = conn.cursor()
            cursor.execute('UPDATE patients SET ward = ? WHERE id = ?', (ward, p_id))
            conn.commit()
            
        # 2. Log Vitals & Prediction
        conn.execute('''
            INSERT INTO vital_logs (patient_id, hr, o2sat, temp, sbp, map, dbp, resp, wbc, lactate, prediction_score, prediction_label, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (p_id, data['HR'], data['O2Sat'], data['Temp'], data['SBP'], data['MAP'], data['DBP'], data['Resp'], data['WBC'], data['Lactate'], result['probability']/100, result['status'], user_id))
        
        # 3. Log Treatment Recommendation
        conn.execute('''
            INSERT INTO treatment_logs (patient_id, risk_score, risk_level, recommendations, user_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (p_id, treatment_data['risk_score'], treatment_data['risk_level'], json.dumps(treatment_data['recommendations']), user_id))
        
        # 4. Log Multi-Disease Predictions
        conn.execute('''
            INSERT INTO disease_predictions (patient_id, sepsis_risk, heart_failure_risk, kidney_failure_risk, pneumonia_risk, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (p_id, multi_result['Sepsis']['risk_score'], multi_result['Heart Failure']['risk_score'], multi_result['Kidney Failure']['risk_score'], multi_result['Pneumonia']['risk_score'], user_id))
        
        # 5. Populate Flattened Patient Predictions for Live Feed
        diseases = ['Sepsis', 'Heart Failure', 'Kidney Failure', 'Pneumonia']
        for disease in diseases:
            risk = multi_result[disease]['risk_score']
            level = "Critical" if risk >= 85.0 else "High" if risk >= 70.0 else "Warning" if risk >= 50.0 else "Stable"
            conn.execute('''
                INSERT INTO patient_predictions (patient_id, patient_uid, user_id, disease_type, risk_score, alert_level)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (p_id, uid, user_id, disease, risk, level))
            
        conn.commit()
        
        # Fire Advanced Alert Engine
        current_risks = {
            'Sepsis': float(multi_result['Sepsis']['risk_score']),
            'Heart Failure': float(multi_result['Heart Failure']['risk_score']),
            'Kidney Failure': float(multi_result['Kidney Failure']['risk_score']),
            'Pneumonia': float(multi_result['Pneumonia']['risk_score'])
        }
        
        # We need the ID of the patient to evaluate alerts
        # Re-fetch patient to ensure we have the latest ID if it was just inserted
        patient = conn.execute('SELECT id FROM patients WHERE patient_uid = ? AND user_id = ?', (uid, user_id)).fetchone()
        evaluate_patient_alerts(patient['id'], {
            'sepsis_risk': current_risks['Sepsis'],
            'heart_failure_risk': current_risks['Heart Failure'],
            'kidney_failure_risk': current_risks['Kidney Failure'],
            'pneumonia_risk': current_risks['Pneumonia']
        }, user_id=user_id)
        
        # Fire Smart Alert System
        process_predictions(patient['id'], uid, current_risks, user_id=user_id)
        
        # Fire Epidemic Background Analysis
        threading.Thread(target=analyze_epidemic_trends, args=(user_id,), daemon=True).start()
        
        conn.close()

        # If the request wants JSON (e.g. from an API call), return JSON
        if request.headers.get('Accept') == 'application/json' or request.content_type == 'application/json':
            return jsonify({
                "patient_id": uid,
                "sepsis_risk": f"{multi_result['Sepsis']['risk_score']}%",
                "heart_failure_risk": f"{multi_result['Heart Failure']['risk_score']}%",
                "kidney_failure_risk": f"{multi_result['Kidney Failure']['risk_score']}%",
                "pneumonia_risk": f"{multi_result['Pneumonia']['risk_score']}%"
            })
        
        return render_template('result.html', result=result, multi_result=multi_result, data=data, uid=uid, heading="Assessment Report")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return render_template('index.html', error=f"NeoGuard Error: {str(e)}", active_page='home')

@app.route('/api/history/<uid>')
@login_required
def get_history(uid):
    """Fetch time-series history for a patient."""
    user_id = session.get('user_id')
    conn = get_db_connection()
    patient = conn.execute('SELECT id FROM patients WHERE patient_uid = ? AND user_id = ?', (uid, user_id)).fetchone()
    if not patient:
        conn.close()
        return jsonify({"error": "Patient UID not found"}), 404
    
    logs = conn.execute('SELECT * FROM vital_logs WHERE patient_id = ? ORDER BY timestamp ASC', (patient['id'],)).fetchall()
    
    # Also fetch disease predictions
    disease_preds = conn.execute('SELECT * FROM disease_predictions WHERE patient_id = ? ORDER BY timestamp ASC', (patient['id'],)).fetchall()
    conn.close()
    
    return jsonify({
        "uid": uid,
        "logs": [dict(log) for log in logs],
        "disease_predictions": [dict(pred) for pred in disease_preds]
    })

@app.route('/api/alerts', methods=['GET'])
@login_required
def get_alerts():
    """Fetch all unacknowledged advanced alerts."""
    user_id = session.get('user_id')
    try:
        alerts = get_active_alerts(user_id=user_id)
        return jsonify({"alerts": alerts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alerts/acknowledge', methods=['POST'])
@login_required
def acknowledge():
    """Acknowledge an alert."""
    data = request.json
    if not data or 'alert_id' not in data or 'staff_name' not in data:
        return jsonify({"error": "Missing alert_id or staff_name"}), 400
        
    user_id = session.get('user_id')
    try:
        success = acknowledge_alert(data['alert_id'], data['staff_name'], user_id=user_id)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alerts/analytics', methods=['GET'])
@login_required
def alert_analytics():
    """Fetch dashboard analytics."""
    user_id = session.get('user_id')
    try:
        stats = get_alert_analytics(user_id=user_id)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/smart_alerts', methods=['GET'])
@login_required
def get_smart_alerts():
    """Fetch recent smart alerts for the dashboard."""
    user_id = session.get('user_id')
    try:
        limit = request.args.get('limit', 50, type=int)
        alerts = get_recent_smart_alerts(limit, user_id=user_id)
        return jsonify({"alerts": alerts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/icu_resources', methods=['GET'])
@login_required
def get_icu_resources():
    """Fetch current 24-hour ICU resource forecast based on underlying risks."""
    user_id = session.get('user_id')
    try:
        scenario = request.args.get('scenario', 'Current')
        prediction_data = analyze_icu_demand(scenario=scenario, user_id=user_id)
        trend = analyze_historical_trends(user_id=user_id)
        prediction_data["historical_trend"] = trend
        return jsonify(prediction_data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/live_feed', methods=['GET'])
@login_required
def get_live_feed():
    """Fetch the latest patient risk predictions across all clinical sessions."""
    user_id = session.get('user_id')
    conn = get_db_connection()
    try:
        # Get latest 20 flattened predictions
        query = '''
            SELECT * FROM patient_predictions 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 20
        '''
        records = conn.execute(query, (user_id,)).fetchall()
        
        feed = []
        for r in records:
            # Format timestamp for better display (e.g. 10:35 AM)
            ts = datetime.strptime(r['timestamp'], '%Y-%m-%d %H:%M:%S')
            display_time = ts.strftime('%I:%M %p')
            
            feed.append({
                "patient_id": r['patient_uid'],
                "disease": r['disease_type'],
                "risk_score": round(r['risk_score'], 1),
                "alert_level": r['alert_level'],
                "timestamp": display_time
            })
            
        return jsonify(feed)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/monitoring/active', methods=['GET'])
@login_required
def get_active_monitoring():
    """Fetch the latest risk status for all unique patients under the current user's session."""
    user_id = session.get('user_id')
    conn = get_db_connection()
    try:
        # Complex query to get the latest prediction for each (patient, disease) pair
        # Simple for demo: Get last 20 unique patient_id snapshots
        query = '''
            SELECT p.patient_uid, r.disease_type, r.risk_score, r.alert_level, r.timestamp
            FROM patient_predictions r
            JOIN (
                SELECT patient_id, MAX(timestamp) as latest_ts
                FROM patient_predictions
                WHERE user_id = ?
                GROUP BY patient_id
            ) latest ON r.patient_id = latest.patient_id AND r.timestamp = latest.latest_ts
            JOIN patients p ON r.patient_id = p.id
            WHERE r.user_id = ?
            ORDER BY r.timestamp DESC
        '''
        records = conn.execute(query, (user_id, user_id)).fetchall()
        
        results = []
        for r in records:
            results.append({
                "patient_id": r['patient_uid'],
                "disease": r['disease_type'],
                "risk_score": round(r['risk_score'], 1),
                "alert_level": r['alert_level'],
                "timestamp": r['timestamp']
            })
            
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/dashboard_stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    """Fetch global KPIs for Command Center Top Bar."""
    user_id = session.get('user_id')
    try:
        conn = get_db_connection()
        # Total Patients
        total_patients = conn.execute('SELECT COUNT(DISTINCT patient_id) as count FROM vital_logs WHERE user_id = ?', (user_id,)).fetchone()['count']
        
        # High Risk Patients (Patients with any Active Alert)
        active_alerts = conn.execute('''
            SELECT COUNT(*) as count 
            FROM advanced_alert_logs a
            JOIN patients p ON a.patient_id = p.id
            WHERE p.user_id = ? AND a.trend_status = 'Escalating' AND a.acknowledged_by IS NULL
        ''', (user_id,)).fetchone()['count']
        
        conn.close()
        
        return jsonify({
            "total_patients": total_patients,
            "active_critical_alerts": active_alerts
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/epidemic/data', methods=['GET'])
@login_required
def get_epidemic_data():
    """Fetch analytics for Epidemic Early Warning System"""
    user_id = session.get('user_id')
    try:
        data = analyze_epidemic_trends(user_id=user_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/epidemic/simulate', methods=['POST'])
@login_required
def trigger_epidemic_sim():
    """Generates mock outbreak data for demonstration"""
    user_id = session.get('user_id')
    try:
        data = simulate_epidemic_data(user_id=user_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/voice_command', methods=['POST'])
@login_required
def voice_command():
    """Handles audio blob from the frontend Voice Assistant."""
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided."}), 400
        
    audio_file = request.files['audio']
    user_id = session.get('user_id')
    
    # Save temporarily
    temp_filename = f"temp_{uuid.uuid4().hex[:8]}.wav"
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
    audio_file.save(temp_path)
    
    # Define an executor that the assistant calls when an intent is found
    def executor(intent_data, transcript):
        intent = intent_data.get("intent")
        
        if intent == "show_history":
            uid = intent_data.get("uid_context")
            if not uid:
                return "Please provide a patient ID to look up their history."
                
            # Naive lookup - just grab the latest prediction for any patient if uid not matched perfectly
            # In a real app we'd search the DB directly
            conn = get_db_connection()
            patient = conn.execute('SELECT * FROM patients WHERE patient_uid LIKE ? AND user_id = ?', (f'%{uid}%', user_id)).fetchone()
            if not patient:
                conn.close()
                return f"I could not find patient {uid} in the database."
                
            preds = conn.execute('SELECT * FROM disease_predictions WHERE patient_id = ? AND user_id = ? ORDER BY timestamp DESC LIMIT 1', (patient['id'], user_id)).fetchone()
            conn.close()
            
            if not preds:
                return f"Patient {uid} has no recent predictions."
                
            return f"Patient {uid} latest assessment. Sepsis risk is {preds['sepsis_risk']} percent. Heart failure risk is {preds['heart_failure_risk']} percent."
            
        elif intent == "predict_risk":
            return "To predict risk, please ensure the patient's vitals are entered on the clinical entry form."
            
        elif intent == "explain_prediction":
            return "The prediction is guided by the explainable AI module. High risk scores are typically driven by elevated heart rate, low oxygen saturation, and abnormal lactate levels."
            
        elif intent == "latest_alerts":
            return "There are currently 2 patients marked as critical in the ICU ward. Please review the central dashboard."
            
        else:
            return "I am the NeoGuard Voice Assistant. I can help you check patient history, predict risks, or explain clinical scores. How can I assist you?"
            
    # Process
    try:
        result = execute_voice_command(temp_path, executor)
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    return jsonify(result)

@app.route('/static/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)

@app.route('/upload_page')
@login_required
def upload_page():
    """Bulk Data Processing Center."""
    return render_template('upload.html', active_page='upload', heading="Batch Intelligence")

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    """Handle batch file upload."""
    if 'file' not in request.files:
        return render_template('upload.html', error="No file segment detected", active_page='upload')
    
    file = request.files['file']
    if file.filename == '':
        return render_template('upload.html', error="No file selected", active_page='upload')
    
    if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls') or file.filename.endswith('.csv')):
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
                
            results_df = get_batch_predictions(df)
            
            if results_df is None:
                return render_template('upload.html', error="Model calibration error.", active_page='upload')
            
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'neoguard_batch_results.xlsx')
            results_df.to_excel(output_path, index=False)
            table_data = results_df.to_dict(orient='records')
            
            return render_template('upload.html', table_data=table_data, download=True, active_page='upload')
        except Exception as e:
            return render_template('upload.html', error=f"Batch Error: {str(e)}", active_page='upload')
    else:
        return render_template('upload.html', error="Invalid format. Supported: .csv, .xlsx", active_page='upload')

@app.route('/download')
def download():
    path = os.path.join(app.config['UPLOAD_FOLDER'], 'neoguard_batch_results.xlsx')
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return "File not found", 404

@app.route('/settings')
@login_required
def settings():
    """System Configuration & Admin."""
    return render_template('settings.html', active_page='settings', heading="System Configuration")

@app.route('/profile')
@login_required
def profile():
    """Chief Medical Officer Profile Page."""
    return render_template('settings.html', active_page='settings', heading="User Profile")

@app.route('/logout')
def logout():
    """Destroy session and securely logout."""
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/settings/save', methods=['POST'])
def save_settings():
    """Save configuration endpoint."""
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "No data received"})
        
    # In a real app, this would write to a DB or config file.
    # For now, we simulate a successful save.
    print(f"[NeoGuard Config Update] Sepsis Threshold: {data.get('sepsis_threshold')}%")
    print(f"[NeoGuard Config Update] Temporal Window: {data.get('temporal_window')}")
    print(f"[NeoGuard Config Update] Auto Refresh: {data.get('auto_refresh')}")
    print(f"[NeoGuard Config Update] Critical Filter: {data.get('critical_filter')}")
    
    return jsonify({"success": True})

@app.route('/api/settings/reset', methods=['POST'])
def reset_settings():
    """Reset configuration to defaults endpoint."""
    # In a real app, this would revert DB/config entries to default.
    return jsonify({"success": True})

# Start Smart Alert Escalation Daemon
def start_escalation_daemon():
    escalation_thread = threading.Thread(target=check_alert_escalations)
    escalation_thread.daemon = True
    escalation_thread.start()

if __name__ == '__main__':
    initialize_system()
    start_escalation_daemon()
    app.run(debug=True, port=5050)
