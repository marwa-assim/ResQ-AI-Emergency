"""
Triage model inference — works on ANY Python version / platform.
Uses scikit-learn RandomForest trained on MIMIC-IV-ED real hospital data.
Falls back to clinical rule-based scoring if model file is missing.
"""
import json
import numpy as np
import os

NUM_COLS = ['temperature', 'heartrate', 'resprate', 'o2sat', 'sbp', 'dbp', 'pain']
MODEL_PATH = "triage_sklearn.pkl"

_pipeline = None

def load_model():
    global _pipeline
    if not os.path.exists(MODEL_PATH):
        print(f"[Triage] {MODEL_PATH} not found — using rule-based fallback.")
        return
    try:
        import joblib
        _pipeline = joblib.load(MODEL_PATH)
        print(f"[Triage] Scikit-learn model loaded: {MODEL_PATH}")
    except Exception as e:
        print(f"[Triage] Failed to load model: {e}. Using fallback.")

load_model()

def predict(features: dict):
    """
    Predict ESI triage priority and risk score.
    features: dict with keys matching NUM_COLS
    returns: (esi_level: int 1-5, risk_score: float 0.0-1.0)
    """
    hr   = float(features.get('heartrate',  80))
    spo2 = float(features.get('o2sat',      98))
    sbp  = float(features.get('sbp',       120))
    rr   = float(features.get('resprate',   16))
    temp = float(features.get('temperature',37))
    dbp  = float(features.get('dbp',        80))
    pain = float(features.get('pain',        0))

    # ── Scikit-learn model (real MIMIC-trained) ──
    if _pipeline is not None:
        try:
            X = np.array([[temp, hr, rr, spo2, sbp, dbp, pain]], dtype=np.float32)
            esi = int(_pipeline.predict(X)[0])
            proba = _pipeline.predict_proba(X)[0]
            # Risk score = weighted probability skewed toward critical classes
            classes = _pipeline.classes_.tolist()
            risk = sum(proba[i] * (1 - (classes[i] - 1) / 4.0) for i in range(len(classes)))
            risk = round(float(np.clip(risk, 0.0, 1.0)), 3)
            return esi, risk
        except Exception as e:
            print(f"[Triage] Inference error: {e}. Using rules.")

    # ── Clinical rule-based fallback ──
    if spo2 < 85 or hr > 160 or hr < 30 or sbp < 70 or rr > 35:
        return 1, 0.97   # Critical
    if spo2 < 92 or hr > 130 or sbp < 90 or rr > 28 or pain >= 9:
        return 2, 0.80   # Emergent
    if spo2 < 95 or hr > 110 or sbp < 100 or rr > 22 or pain >= 6:
        return 3, 0.55   # Urgent
    if pain >= 3 or hr > 95 or temp > 38.5:
        return 4, 0.30   # Less urgent
    return 5, 0.10       # Non-urgent
