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
except ImportError:
    MINDSPORE_AVAILABLE = False
    print("[Warning] MindSpore not installed locally. Operating in Safe Demo Mode.")

MODEL_CKPT = "mimic_risk_model.ckpt"
SCALING_JSON = "mindspore_scaling.json"

model = None
stats = None

def load_model():
    global model, stats
    if not MINDSPORE_AVAILABLE:
        print("[MindSpore] Library missing. Skipping checkpoint load.")
        return
        
    if os.path.exists(MODEL_CKPT) and os.path.exists(SCALING_JSON):
        # Load Stats
        with open(SCALING_JSON, "r") as f:
            stats = json.load(f)
            
        # Load Net
        net = RiskModel(input_dim=7, hidden_dim=64, output_dim=5)
        param_dict = load_checkpoint(MODEL_CKPT)
        load_param_into_net(net, param_dict)
        model = net
        print("[MindSpore] Model Loaded Successfully: " + MODEL_CKPT)
    else:
        print("[MindSpore] Checkpoint not found. Using Fallback.")

# Initial Load
load_model()

def predict(features):
    """
    Predict using MindSpore Model.
    features: dict { 'heartrate': val, ... }
    Returns: (ESI Level [1-5], Risk Score [0.0-1.0])
    """
    global model
    
    # Fallback
    if not model or not stats:
        hr = features.get('heartrate', 80)
        spo2 = features.get('o2sat', 98)
        if spo2 < 90 or hr > 120: return 1, 0.95
        return 3, 0.5

    # Preprocess
    input_vec = []
    cols = ['temperature', 'heartrate', 'resprate', 'o2sat', 'sbp', 'dbp', 'pain']
    
    for col in cols:
        val = features.get(col, 0)
        if val is None: val = 0
        
        # Scale
        mu = stats[col]['mean']
        sigma = stats[col]['std']
        scaled_val = (val - mu) / sigma
        input_vec.append(scaled_val)
        
    if not MINDSPORE_AVAILABLE:
        # If MindSpore is uninstalled but stats exist, we fallback to a safe static logic
        return _fallback_predict(features)
        
    # Inference
    input_tensor = Tensor(np.array([input_vec], dtype=np.float32))
    output = model(input_tensor)
    probs = output.asnumpy()[0] # [prob_class0, prob_class1, ...]
    
    # Logic: Convert Raw Logits to Probabilities using Softmax
    exp_probs = np.exp(probs - np.max(probs)) # stable softmax
    softmax_probs = exp_probs / np.sum(exp_probs)
    
    pred_class = np.argmax(softmax_probs)
    esi_level = pred_class + 1 # 0-index to 1-5
    
    # Risk Score: Sum of probs for ESI 1 & 2 (High Risk)
    risk_score = float(softmax_probs[0] + softmax_probs[1]) 
    
    return int(esi_level), float(risk_score)

def _fallback_predict(features):
    hr = features.get('heartrate', 80)
    spo2 = features.get('o2sat', 98)
    if spo2 < 90 or hr > 120: return 1, 0.95
    return 3, 0.5
