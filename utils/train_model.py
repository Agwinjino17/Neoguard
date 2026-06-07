import pandas as pd
import numpy as np
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from xgboost import XGBClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

def create_sample_dataset(filepath):
    """
    Creates a sample sepsis dataset for demonstration/initialization purposes.
    Saves it as a CSV file.
    """
    print("Dataset not found → creating sample dataset")
    np.random.seed(42)
    n_samples = 1000
    
    # Generate realistic ranges for patient data
    data = {
        'HR': np.random.normal(80, 15, n_samples),
        'O2Sat': np.random.normal(97, 2, n_samples),
        'Temp': np.random.normal(37, 1, n_samples),
        'SBP': np.random.normal(120, 20, n_samples),
        'MAP': np.random.normal(85, 15, n_samples),
        'DBP': np.random.normal(80, 15, n_samples),
        'Resp': np.random.normal(18, 5, n_samples),
        'WBC': np.random.normal(10, 4, n_samples),
        'Lactate': np.random.normal(1.5, 1, n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # Create a synthetic target 'SepsisLabel' based on clinical criteria
    # Sepsis is more likely if: HR > 90, Temp > 38, Resp > 20, WBC > 12 OR < 4, etc.
    sepsis_risk = (
        (df['HR'] > 90).astype(int) * 2 +
        (df['Temp'] > 37.5).astype(int) * 1.5 +
        (df['O2Sat'] < 95).astype(int) * 2 +
        (df['Resp'] > 20).astype(int) * 1.5 +
        (df['Lactate'] > 2.0).astype(int) * 3 +
        (df['WBC'] > 12).astype(int) * 1
    )
    
    # Normalize risk and apply a threshold for binary label
    df['SepsisLabel'] = (sepsis_risk > sepsis_risk.median()).astype(int)
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"Sample dataset saved to {filepath}")

def train_model():
    """
    Main training function.
    - Loads dataset (creates sample if missing)
    - Preprocesses data
    - Trains hybrid ensemble
    - Saves model and scaler
    """
    dataset_path = os.path.join('dataset', 'sepsis_data.csv')
    model_dir = 'model'
    model_path = os.path.join(model_dir, 'model.pkl')
    
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
        
    if not os.path.exists(dataset_path):
        create_sample_dataset(dataset_path)

    try:
        print("Training model...")
        df = pd.read_csv(dataset_path)
        
        # Check for target column
        if 'SepsisLabel' not in df.columns:
            return False, "Target column 'SepsisLabel' missing from dataset."
            
        # Feature selection
        features = ['HR', 'O2Sat', 'Temp', 'SBP', 'MAP', 'DBP', 'Resp', 'WBC', 'Lactate']
        for feat in features:
            if feat not in df.columns:
                df[feat] = np.nan
        
        # Missing value handling
        df[features] = df[features].ffill().fillna(df[features].mean())
        
        X = df[features]
        y = df['SepsisLabel']
        
        # Train-Test Split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        # Scaling
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Hybrid Model Ensemble
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
        acc = accuracy_score(y_test, y_pred)
        
        # Save Model Bundle
        model_bundle = {
            'model': ensemble,
            'scaler': scaler,
            'features': features,
            'accuracy': acc
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_bundle, f)
            
        print(f"Model successfully trained and saved to {model_path} (Accuracy: {acc:.4f})")
        return True, "Training successful"
        
    except Exception as e:
        print(f"Training failed: {str(e)}")
        return False, f"Internal Error: {str(e)}"

if __name__ == "__main__":
    train_model()
