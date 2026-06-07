import pandas as pd
import numpy as np

def handle_missing_values(df):
    """Handle missing values using mean imputation and forward fill."""
    # Forward fill for time-series consistency if available
    df = df.ffill()
    # Fill remaining NaNs with mean of the column
    return df.fillna(df.mean())

def preprocess_input(data, scaler=None, required_features=None):
    """
    Preprocess raw input data (dict or DataFrame).
    - Convert to DataFrame
    - Align features
    - Handle missing values
    - Scale if scaler is provided
    """
    if required_features is None:
        required_features = ['HR', 'O2Sat', 'Temp', 'SBP', 'MAP', 'DBP', 'Resp', 'WBC', 'Lactate']
    
    if isinstance(data, dict):
        df = pd.DataFrame([data])
    elif isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data.copy()
    
    # Ensure all required features are present
    for feat in required_features:
        if feat not in df.columns:
            df[feat] = np.nan
            
    # Reorder columns to match training order
    df = df[required_features]
    
    # Handle missing values
    df = handle_missing_values(df)
    
    # Final check: if still NaNs (e.g. all values in a column were NaN), fill with 0
    df = df.fillna(0)
    
    if scaler:
        df_scaled = scaler.transform(df)
        return df_scaled
    
    return df.values
