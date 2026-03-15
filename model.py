"""
Triage model inference using Huawei MindSpore neural network.
Trained on MIMIC-IV-ED real hospital data (80k samples).
Architecture: Dense(7->64) -> ReLU -> Dense(64->32) -> ReLU -> Dense(32->5)
Falls back to clinical rules if MindSpore is unavailable.
"""
import json
import numpy as np
import os
import math

try:
    import mindspore
    from mindspore import load_checkpoint, load_param_into_net, Tensor
    import mindspore.context as context
    from train_risk_model_mindspore import RiskModel
    context.set_context(mode=context.GRAPH_MODE, device_target="CPU")
    MINDSPORE_AVAILABLE = True
    print("[MindSpore] Library loaded successfully.")
except ImportError:
    MINDSPORE_AVAILABLE = False
    print("[MindSpore] Library not installed. Using clinical rule-based fallback.")

MODEL_CKPT  = "mimic_risk_model.ckpt"
SCALING_JSON = "mindspore_scaling.json"

_model = None
_stats = None

def load_model():
    global _model, _stats
    if not MINDSPORE_AVAILABLE:
        return
    if os.path.exists(MODEL_CKPT) and os.path.exists(SCALING_JSON):
        with open(SCALING_JSON, "r") as f:
            _stats = json.load(f)
        net = RiskModel(input_dim=7, hidden_dim=64, output_dim=5)
        param_dict = load_checkpoint(MODEL_CKPT)
        load_param_into_net(net, param_dict)
        _model = net
        print(f"[MindSpore] Model loaded: {MODEL_CKPT}")
    else:
        print("[MindSpore] Checkpoint not found. Using fallback.")

load_model()

def predict(features: dict):
    """
    Predict ESI triage level and risk score.
    features: dict with keys: temperature, heartrate, resprate, o2sat, sbp, dbp, pain
    Returns: (esi_level: int 1-5, risk_score: float 0.0-1.0)
    """
    NUM_COLS = ['temperature', 'heartrate', 'resprate', 'o2sat', 'sbp', 'dbp', 'pain']

    hr   = float(features.get('heartrate',   80))
    spo2 = float(features.get('o2sat',       98))
    sbp  = float(features.get('sbp',        120))
    rr   = float(features.get('resprate',    16))
    temp = float(features.get('temperature', 37))
    dbp  = float(features.get('dbp',         80))
    pain = float(features.get('pain',         0))

    # ── MindSpore neural network inference ──
    if _model is not None and _stats is not None:
        try:
            raw = [temp, hr, rr, spo2, sbp, dbp, pain]
            scaled = []
            for i, col in enumerate(NUM_COLS):
                mu = _stats[col]['mean']
                sigma = _stats[col]['std'] or 1.0
                scaled.append(max(-5.0, min(5.0, (raw[i] - mu) / sigma)))

            x = Tensor(np.array([scaled], dtype=np.float32))
            logits = _model(x).asnumpy()[0]

            # Softmax to get class probabilities
            e = np.exp(logits - np.max(logits))
            proba = e / e.sum()

            esi = int(np.argmax(proba)) + 1  # classes are 0-indexed
            # Risk = weighted probability (class 1 = highest risk)
            risk = sum(proba[i] * (1 - i / 4.0) for i in range(5))
            return esi, round(float(np.clip(risk, 0.0, 1.0)), 3)
        except Exception as e:
            print(f"[MindSpore] Inference error: {e}. Using rules.")

    # ── Clinical rule-based fallback ──
    if spo2 < 85 or hr > 160 or hr < 30 or sbp < 70 or rr > 35:
        return 1, 0.97
    if spo2 < 92 or hr > 130 or sbp < 90 or rr > 28 or pain >= 9:
        return 2, 0.80
    if spo2 < 95 or hr > 110 or sbp < 100 or rr > 22 or pain >= 6:
        return 3, 0.55
    if pain >= 3 or hr > 95 or temp > 38.5:
        return 4, 0.30
    return 5, 0.10
