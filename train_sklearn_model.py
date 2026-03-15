"""
Trains a scikit-learn RandomForest triage model on MIMIC-IV-ED data.
Falls back to synthetic data if MIMIC is unavailable.
Saves: triage_sklearn.pkl
Run: python train_sklearn_model.py
"""
import numpy as np
import pandas as pd
import joblib, os, json
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

NUM_COLS = ['temperature', 'heartrate', 'resprate', 'o2sat', 'sbp', 'dbp', 'pain']
MODEL_PATH = "triage_sklearn.pkl"
TRIAGE_PATH = "data/mimic/mimic-iv-ed-2.2/ed/triage.csv.gz"

def load_mimic():
    if not os.path.exists(TRIAGE_PATH):
        return None, None
    print("Loading MIMIC-IV-ED data...")
    df = pd.read_csv(TRIAGE_PATH, compression='gzip')
    df = df.dropna(subset=['acuity'])
    df['acuity'] = df['acuity'].astype(int)
    for col in NUM_COLS:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df[col] = df[col].fillna(df[col].median())
    X = df[NUM_COLS].values.astype(np.float32)
    y = df['acuity'].values.astype(int)
    return X, y

def make_synthetic():
    """Generate realistic synthetic triage data matching ESI 1-5 distribution."""
    print("MIMIC data not found. Generating synthetic training data...")
    np.random.seed(42)
    rows = []
    # ESI 1 - Critical (5%)
    for _ in range(500):
        rows.append([37.2, np.random.randint(130,180), np.random.randint(25,35),
                     np.random.randint(80,88), np.random.randint(60,80),
                     np.random.randint(40,60), np.random.randint(8,10), 1])
    # ESI 2 - Emergent (15%)
    for _ in range(1500):
        rows.append([37.5, np.random.randint(110,135), np.random.randint(20,26),
                     np.random.randint(88,93), np.random.randint(80,100),
                     np.random.randint(55,70), np.random.randint(6,9), 2])
    # ESI 3 - Urgent (30%)
    for _ in range(3000):
        rows.append([37.0, np.random.randint(85,115), np.random.randint(16,22),
                     np.random.randint(93,97), np.random.randint(100,130),
                     np.random.randint(65,85), np.random.randint(4,7), 3])
    # ESI 4 - Less Urgent (30%)
    for _ in range(3000):
        rows.append([36.8, np.random.randint(65,90), np.random.randint(14,18),
                     np.random.randint(96,99), np.random.randint(110,140),
                     np.random.randint(70,90), np.random.randint(2,5), 4])
    # ESI 5 - Non-urgent (20%)
    for _ in range(2000):
        rows.append([36.6, np.random.randint(60,80), np.random.randint(12,16),
                     np.random.randint(97,100), np.random.randint(115,135),
                     np.random.randint(70,85), np.random.randint(0,3), 5])

    df = pd.DataFrame(rows, columns=NUM_COLS + ['acuity'])
    X = df[NUM_COLS].values.astype(np.float32)
    y = df['acuity'].values.astype(int)
    return X, y

def train():
    X, y = load_mimic()
    if X is None:
        X, y = make_synthetic()

    # Use up to 100k samples
    if len(X) > 100000:
        idx = np.random.choice(len(X), 100000, replace=False)
        X, y = X[idx], y[idx]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    print(f"Training on {len(X_train)} samples...")
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', RandomForestClassifier(n_estimators=200, max_depth=15,
                                       n_jobs=-1, random_state=42,
                                       class_weight='balanced'))
    ])
    pipeline.fit(X_train, y_train)

    # Evaluate
    preds = pipeline.predict(X_test)
    acc = np.mean(preds == y_test)
    print(f"\nAccuracy: {acc:.2%}")
    print(classification_report(y_test, preds, zero_division=0))

    # Save
    joblib.dump(pipeline, MODEL_PATH)
    print(f"\nModel saved: {MODEL_PATH}")

    # Save feature list for inference validation
    with open("sklearn_features.json", "w") as f:
        json.dump({"features": NUM_COLS}, f)

if __name__ == "__main__":
    train()
