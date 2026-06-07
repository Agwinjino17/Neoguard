🏥 NeoGuard — Neonatal Sepsis Detection & Clinical Intelligence System

An AI-powered clinical decision support system for early detection of neonatal sepsis and multi-disease risk prediction, built for real-world hospital environments.


📌 Table of Contents

Overview
Key Features
Tech Stack
Project Structure
Installation & Setup
Usage
ML Models
API Endpoints
Database Schema
Team


Overview
NeoGuard is a full-stack AI hospital intelligence platform focused on neonatal sepsis detection using ensemble machine learning. It provides real-time patient monitoring, predictive risk scoring, smart alerting, ICU resource forecasting, and epidemic early-warning capabilities — all through a secure, role-based web interface.
Originally developed as a Final Year Project (B.E. CSE, Anna University — 2026 batch).

Key Features
FeatureDescription🤖 Sepsis Risk PredictionReal-time ML-based sepsis risk scoring from patient vitals🧬 Multi-Disease PredictionSimultaneous risk assessment for Pneumonia, Heart Failure, and more🚨 Smart Alert EngineTiered alert system with auto-escalation for critical patients📊 Temporal Analytics DashboardTime-series visualization of patient trends and predictions🏥 ICU Resource PredictorForecasts ICU bed demand based on admission patterns🦠 Epidemic Early WarningOutbreak trend analysis and simulation engine🎙️ Voice AssistantAudio-based clinical query interface (patient history, risk status)📁 Batch ProcessingBulk CSV/Excel upload for population-level predictions👥 Multi-tenant ArchitectureRole-based access (Doctor, Nurse, Admin, Staff) with data isolation🔒 Secure AuthenticationSession-based login with password hashing and login audit logs

Tech Stack
Backend

Python 3.11
Flask — Web framework & REST API
SQLite — Database (neoguard.db)
SQLAlchemy / sqlite3 — ORM & DB access
Werkzeug — Password hashing & security

Machine Learning

scikit-learn — Random Forest, MLP Classifier
XGBoost — Gradient boosting for ensemble predictions
pandas / numpy — Data preprocessing
pickle — Model serialization

Frontend

Jinja2 — Server-side templating
HTML5 / CSS3 / JavaScript — UI
Bootstrap — Responsive layout

Utilities

smtplib — Email alert system
threading — Background escalation daemon
Selenium — Automated dashboard testing


Project Structure
NeoGuard/
├── app.py                        # Main Flask application
├── requirements.txt              # Python dependencies
├── neoguard.db                   # SQLite database
├── email_config.json             # SMTP email configuration
├── staff_directory.json          # Staff contact directory
│
├── dataset/
│   └── sepsis_data.csv           # Training dataset
│
├── model/
│   ├── model.pkl                 # Primary sepsis model
│   └── pneumonia_model.pkl       # Multi-disease models
│
├── utils/
│   ├── predict.py                # Single & batch prediction logic
│   ├── train_model.py            # Model training pipeline
│   ├── database.py               # DB init & connection helpers
│   ├── treatment_recommendation.py  # Clinical treatment suggestion engine
│   ├── multi_disease_predictor.py   # Multi-disease ML inference
│   ├── voice_assistant.py           # Voice command processing
│   ├── advanced_alert_engine.py     # Alert evaluation & analytics
│   ├── smart_alert_system.py        # Smart alert processing & escalation
│   ├── icu_resource_predictor.py    # ICU demand forecasting
│   └── epidemic_outbreak_engine.py  # Epidemic simulation & analysis
│
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── index.html                # Clinical entry portal
│   ├── dashboard.html            # Temporal analytics
│   ├── patients.html             # Patient records
│   ├── upload.html               # Batch processing
│   └── settings.html             # System configuration
│
├── static/                       # CSS, JS, images
├── uploads/                      # Uploaded files & batch results
│
├── db_health_check.py            # Database integrity checker
├── verify_email.py               # Email system verification
├── screenshot_test.py            # UI screenshot automation
└── test_dashboard.py             # Dashboard Selenium tests

Installation & Setup
1. Clone the Repository
bashgit clone https://github.com/Agwinjino17/neoguard.git
cd neoguard
2. Create Virtual Environment
bashpython -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
3. Install Dependencies
bashpip install -r requirements.txt
4. Configure Email Alerts (Optional)
Edit email_config.json:
json{
    "sender_email": "your_email@gmail.com",
    "sender_password": "YOUR_GMAIL_APP_PASSWORD",
    "receiver_email": "alert_receiver@gmail.com",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "alert_enabled": true
}

Use a Gmail App Password (not your regular password). Generate at: Google Account → Security → App Passwords

5. Run the Application
bashpython app.py
The app will auto-initialize the database and train ML models on first launch.
Open: http://127.0.0.1:5050

Usage

Register a clinical account with your role (Doctor / Nurse / Admin / Staff)
Login with your credentials
Enter patient vitals on the Clinical Entry Portal to get instant sepsis risk scores
Monitor all patients via the Central Records and Analytics Dashboard
Use Batch Upload to process multiple patients via CSV/Excel
Critical patients trigger automatic Smart Alerts with escalation
Voice commands available via the built-in Voice Assistant


ML Models
Primary Model — Sepsis Detection
AlgorithmRoleRandom ForestEnsemble base learnerXGBoostGradient boosted classifierMLP (Neural Network)Deep pattern recognition
Input Features (Vitals):

Heart Rate (HR) — 20 to 300 bpm
Oxygen Saturation (SpO2)
Temperature
Respiratory Rate
Blood Pressure (Systolic / Diastolic)
Lactate levels
WBC count

Output: Sepsis Risk % + Risk Category (Low / Moderate / High / Critical)
Multi-Disease Predictor

Pneumonia Risk
Heart Failure Risk
(Extensible to additional conditions)


API Endpoints
MethodEndpointDescriptionPOST/api/predictSingle patient sepsis predictionPOST/api/multi_predictMulti-disease risk predictionGET/api/dashboard_dataDashboard time-series dataGET/api/alerts/activeFetch active clinical alertsPOST/api/alerts/acknowledgeAcknowledge an alertGET/api/icu/demandICU resource demand forecastGET/api/epidemic/dataEpidemic trend analyticsPOST/api/epidemic/simulateTrigger outbreak simulationPOST/api/voice_commandProcess voice audio commandGET/api/summaryPatient + alert summary counts

Database Schema
Tables:

users — Staff accounts with roles
patients — Patient records (multi-tenant by user_id)
vital_logs — Historical vitals per patient
disease_predictions — ML prediction history
treatment_logs — Clinical treatment records
advanced_alert_logs — Alert events
smart_alert_logs — Escalation-aware alerts
icu_resource_predictions — ICU demand forecasts
patient_predictions — Prediction snapshots
epidemic_alerts — Outbreak warning records
login_logs — Authentication audit trail


Team
Final Year Project — B.E. Computer Science & Engineering
Anna University | DMI Engineering College | Batch 2022–2026
NameRoleAgwin Jino JML & Backend DeveloperSathish KumarBackend & DatabaseMadhan SenthilFrontend & Integration

⚠️ Disclaimer
NeoGuard is an academic research prototype. It is not certified for clinical use. All predictions are for demonstration and research purposes only. Do not use for real medical decision-making without proper clinical validation and regulatory approval.

Built with ❤️ for neonates who can't speak for themselves.
