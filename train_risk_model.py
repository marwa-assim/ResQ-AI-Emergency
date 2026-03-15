import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
import joblib
import os

# Data Paths
DATA_DIR = r"data/mimic/mimic-iv-ed-2.2/ed"
TRIAGE_PATH = os.path.join(DATA_DIR, "triage.csv.gz")

def train():
    print("Loading Triage Data...")
    if not os.path.exists(TRIAGE_PATH):
        print(f"Error: {TRIAGE_PATH} not found.")
        return

    # Load Triage Data
    df = pd.read_csv(TRIAGE_PATH, compression='gzip')
    
    # Filter valid acuity (Target)
    df = df.dropna(subset=['acuity'])
    df['acuity'] = df['acuity'].astype(int)
    
    # Target: Acuity is 1-5.
    y = df['acuity']
    
    # Features
    # Numeric
    num_cols = ['temperature', 'heartrate', 'resprate', 'o2sat', 'sbp', 'dbp', 'pain']
    # Text
    text_col = 'chiefcomplaint'
    
    X = df[num_cols + [text_col]].copy()
    
    # Cleaning Numeric
    # 'pain' is often mixture of numbers and text in MIMIC. For simplicity, we coerce to numeric.
    X['pain'] = pd.to_numeric(X['pain'], errors='coerce')
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print(f"Training on {len(X_train)} samples...")
    
    # Preprocessing Pipeline
    # 1. Numeric: Impute Median -> Scale
    num_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    
    # 2. Text: TF-IDF (Top 500 words to keep model light)
    text_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='')), # Handle missing text
        ('tfidf', TfidfVectorizer(max_features=500, stop_words='english'))
    ])
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', num_transformer, num_cols),
            ('text', text_transformer, text_col)
        ])
    
    # Full Pipeline
    # Using RandomForest instead of XGBoost due to env issues
    clf = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced',
            n_jobs=-1
        ))
    ])
    
    # Train
    clf.fit(X_train, y_train)
    
    # Evaluate
    print("\nEvaluating...")
    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred))
    
    # Save
    print("Saving Model...")
    joblib.dump(clf, 'mimic_risk_model.joblib')
    # Save vectorizer separately? No, it's inside the pipeline!
    # joblib.dump(clf['preprocessor'], 'tfidf_vectorizer.joblib') 
    # Just saving the whole pipeline is enough.
    
    print("Done! Model saved to mimic_risk_model.joblib")

if __name__ == "__main__":
    train()
