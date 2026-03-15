import pandas as pd
import numpy as np
import json
import os
import math

# Data Paths
DATA_DIR = r"data/mimic/mimic-iv-ed-2.2/ed"
TRIAGE_PATH = os.path.join(DATA_DIR, "triage.csv.gz")
# TRIAGE_PATH = "triage_data.csv"

def train_custom_model():
    print("Loading Triage Data (Custom Numpy Implementation)...")
    if not os.path.exists(TRIAGE_PATH):
        print(f"Error: {TRIAGE_PATH} not found.")
        return

    # Load Triage Data
    df = pd.read_csv(TRIAGE_PATH, compression='gzip')
    df = df.dropna(subset=['acuity'])
    df['acuity'] = df['acuity'].astype(int)
    
    # Features
    num_cols = ['temperature', 'heartrate', 'resprate', 'o2sat', 'sbp', 'dbp', 'pain']
    # We will ignore 'chiefcomplaint' text for this simple numpy model to keep it robust
    
    # Clean Numeric
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Impute Median (Manual)
    medians = {}
    for col in num_cols:
        med = df[col].median()
        if pd.isna(med): med = 0
        df[col] = df[col].fillna(med)
        medians[col] = float(med)
        
    # Standardize (Manual Z-Score)
    means = {}
    stds = {}
    for col in num_cols:
        mu = df[col].mean()
        sigma = df[col].std()
        if sigma == 0: sigma = 1
        means[col] = float(mu)
        stds[col] = float(sigma)
        df[col] = (df[col] - mu) / sigma
        
    # Train: Nearest Centroid Classifier
    # Calculate mean vector for each class (1, 2, 3, 4, 5)
    centroids = {}
    class_counts = df['acuity'].value_counts()
    
    print("Training Centroids...")
    for acuity in sorted(df['acuity'].unique()):
        subset = df[df['acuity'] == acuity]
        centroid = []
        for col in num_cols:
            centroid.append(float(subset[col].mean()))
        centroids[str(acuity)] = centroid
        print(f"Class {acuity}: {len(subset)} samples")

    # Save Model
    model_data = {
        "features": num_cols,
        "scaling": {
            "medians": medians,
            "means": means,
            "stds": stds
        },
        "centroids": centroids
    }
    
    with open("mimic_risk_model.json", "w") as f:
        json.dump(model_data, f, indent=2)
        
    print("Done! Saved mimic_risk_model.json")

if __name__ == "__main__":
    train_custom_model()
