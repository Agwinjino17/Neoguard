import pandas as pd
import numpy as np
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from xgboost import XGBClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, '..', 'model')
DATASET_PATH = os.path.join(BASE_DIR, '..', 'dataset', 'sepsis_data.csv')

DISEASES = {
    'Sepsis': 'sepsis_model.pkl',
    'Heart Failure': 'heart_failure_model.pkl',
    'Kidney Failure': 'kidney_failure_model.pkl',
    'Pneumonia': 'pneumonia_model.pkl'
}

def generate_multi_disease_labels(df):
    """Generate synthetic labels for other diseases based on physiological markers."""
    np.random.seed(42)
    
    # Heart Failure risk: High HR, High MAP, Low O2
    hf_risk = (
        (df['HR'] > 100).astype(int) * 2 +
        (df['MAP'] > 90).astype(int) * 1.5 +
        (df['O2Sat'] < 92).astype(int) * 2
    )
    df['Heart Failure_Label'] = (hf_risk > hf_risk.quantile(0.7)).astype(int)
    
    # Kidney Failure risk: High MAP, High DBP, High Lactate
    kf_risk = (
        (df['MAP'] > 85).astype(int) * 1.5 +
        (df['DBP'] > 90).astype(int) * 2 +
        (df['Lactate'] > 2.5).astype(int) * 3
    )
    df['Kidney Failure_Label'] = (kf_risk > kf_risk.quantile(0.8)).astype(int)
    
    # Pneumonia risk: High Temp, High Resp, Low O2, High WBC
    pneu_risk = (
        (df['Temp'] > 38.0).astype(int) * 2 +
        (df['Resp'] > 22).astype(int) * 2 +
        (df['O2Sat'] < 94).astype(int) * 2 +
        (df['WBC'] > 11).astype(int) * 1.5
    )
    df['Pneumonia_Label'] = (pneu_risk > pneu_risk.quantile(0.75)).astype(int)
    
    return df

def train_multi_disease_models():
    """Train separate ensemble models for all target diseases."""
    print("Initializing Multi-Disease Training Pipeline...")
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)
        
    try:
        df = pd.read_csv(DATASET_PATH)
        
        # Sepsis target should already be in the data from train_model.py
        if 'SepsisLabel' in df.columns:
            df['Sepsis_Label'] = df['SepsisLabel']
        else:
            return False, "Target SepsisLabel missing from dataset."
            
        df = generate_multi_disease_labels(df)
        
        features = ['HR', 'O2Sat', 'Temp', 'SBP', 'MAP', 'DBP', 'Resp', 'WBC', 'Lactate']
        df[features] = df[features].ffill().fillna(df[features].mean())
        
        X = df[features]
        metrics_report = {}
        
        for disease, model_filename in DISEASES.items():
            print(f"Training Model for {disease}...")
            y = df[f"{disease}_Label"]
            
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
            
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            lr = LogisticRegression(random_state=42)
            rf = RandomForestClassifier(n_estimators=100, random_state=42)
            xgb = XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)
            
            ensemble = VotingClassifier(
                estimators=[('lr', lr), ('rf', rf), ('xgb', xgb)],
                voting='soft'
            )
            
            ensemble.fit(X_train_scaled, y_train)
            
            # Validation
            y_pred = ensemble.predict(X_test_scaled)
            probs = ensemble.predict_proba(X_test_scaled)[:, 1]
            
            acc = accuracy_score(y_test, y_pred)
            prec = precision_score(y_test, y_pred, zero_division=0)
            rec = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            
            metrics = {
                'accuracy': round(acc * 100, 1),
                'precision': round(prec * 100, 1),
                'recall': round(rec * 100, 1),
                'f1_score': round(f1 * 100, 1)
            }
            
            metrics_report[disease] = metrics
            
            # Save Model Bundle
            model_bundle = {
                'model': ensemble,
                'scaler': scaler,
                'features': features,
                'metrics': metrics
            }
            
            model_path = os.path.join(MODEL_DIR, model_filename)
            with open(model_path, 'wb') as f:
                pickle.dump(model_bundle, f)
                
            print(f"> {disease} model saved. Acc: {metrics['accuracy']}%")
            
        # Save overarching metrics report for easy access
        with open(os.path.join(MODEL_DIR, 'multi_disease_metrics.json'), 'w') as f:
            import json
            json.dump(metrics_report, f)
            
        return True, "Multi-Disease Training successful"
        
    except Exception as e:
        print(f"Multi-Disease Training failed: {str(e)}")
        return False, f"Internal Error: {str(e)}"

def get_risk_level(prob):
    """Convert probability value to risk level."""
    if prob <= 30:
        return 'LOW'
    elif prob <= 60:
        return 'MODERATE'
    elif prob <= 80:
        return 'HIGH'
    else:
        return 'CRITICAL'

def get_multi_prediction(input_data):
    """
    Get predictions for multiple diseases from a single set of patient data.
    """
    results = {}
    
    # Format input
    import numpy as np
    
    for disease, model_filename in DISEASES.items():
        model_path = os.path.join(MODEL_DIR, model_filename)
        if not os.path.exists(model_path):
            return {"error": f"Model for {disease} not found. Please train models."}
            
        with open(model_path, 'rb') as f:
            bundle = pickle.load(f)
            
        model = bundle['model']
        scaler = bundle['scaler']
        features = bundle['features']
        
        # Preprocess input
        try:
            input_df = pd.DataFrame([input_data])
            for feat in features:
                if feat not in input_df.columns:
                    input_df[feat] = 0.0
            input_df = input_df[features]
            X_scaled = scaler.transform(input_df)
            
            probability = float(model.predict_proba(X_scaled)[0][1]) * 100
            
            results[disease] = {
                'risk_score': round(probability, 1),
                'risk_level': get_risk_level(probability),
                'metrics': bundle.get('metrics', {})
            }
        except Exception as e:
            return {"error": f"Error calculating risk for {disease}: {str(e)}"}
            
    return results

if __name__ == "__main__":
    train_multi_disease_models()
