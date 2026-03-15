import pandas as pd
import numpy as np
import os
import mindspore
import mindspore.nn as nn
import mindspore.ops as ops
from mindspore import Tensor, context
from mindspore.train import Model
from mindspore.train.callback import LossMonitor

# Set Context (CPU for Windows)
context.set_context(mode=context.GRAPH_MODE, device_target="CPU")

# Data Paths
DATA_DIR = r"data/mimic/mimic-iv-ed-2.2/ed"
TRIAGE_PATH = os.path.join(DATA_DIR, "triage.csv.gz")
MODEL_PATH = "mimic_risk_model.ckpt"

# Features
NUM_COLS = ['temperature', 'heartrate', 'resprate', 'o2sat', 'sbp', 'dbp', 'pain']
NUM_CLASSES = 5 # Acuity 1-5

class RiskModel(nn.Cell):
    def __init__(self, input_dim, hidden_dim=64, output_dim=5):
        super(RiskModel, self).__init__()
        self.fc1 = nn.Dense(input_dim, hidden_dim)
        self.relu = nn.ReLU()
        # Second layer reduced by half
        self.fc2 = nn.Dense(hidden_dim, int(hidden_dim/2)) 
        self.fc3 = nn.Dense(int(hidden_dim/2), output_dim)
        
    def construct(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        x = self.relu(x)
        x = self.fc3(x)
        return x

def preprocess_data():
    print("Loading MIMIC Data...")
    if not os.path.exists(TRIAGE_PATH):
        print("Data not found!")
        return None, None

    df = pd.read_csv(TRIAGE_PATH, compression='gzip')
    df = df.dropna(subset=['acuity'])
    df['acuity'] = df['acuity'].astype(int) - 1 # 0-indexed for CrossEntropy
    
    # Simple Imputation & Scaling
    stats = {}
    for col in NUM_COLS:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        med = df[col].median()
        if pd.isna(med): med = 0
        df[col] = df[col].fillna(med)
        
        mu = df[col].mean()
        sigma = df[col].std()
        if sigma == 0: sigma = 1
        # Standardize and Clip Outliers (Robust Scaling)
        df[col] = ((df[col] - mu) / sigma).clip(-5, 5)
        stats[col] = {'mean': float(mu), 'std': float(sigma)}
    
    X = df[NUM_COLS].values.astype(np.float32)
    y = df['acuity'].values.astype(np.int32)
    
    # Save stats for inference
    import json
    with open("mindspore_scaling.json", "w") as f:
        json.dump(stats, f)
        
    return X, y

def train():
    X, y = preprocess_data()
    if X is None: return

    # Limit samples (Increased for Accuracy - 100k samples)
    if len(X) > 100000:
        indices = np.random.choice(len(X), 100000, replace=False)
        X = X[indices]
        y = y[indices]

    # Split Train/Test (80/20)
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # Convert to Tensor (Batch size increased for stability)
    dataset = mindspore.dataset.NumpySlicesDataset({"data": X_train, "label": y_train}, shuffle=True)
    dataset = dataset.batch(64)
    
    # Model (Larger Capacity)
    # Input -> 64 -> 32 -> Output
    net = RiskModel(input_dim=len(NUM_COLS), hidden_dim=64, output_dim=NUM_CLASSES)
    
    # Loss & Optimizer
    loss = nn.SoftmaxCrossEntropyWithLogits(sparse=True, reduction='mean')
    opt = nn.Adam(net.trainable_params(), learning_rate=0.001) # Reduced LR to prevent NaN
    
    model = Model(net, loss_fn=loss, optimizer=opt, metrics={'acc'})
    
    print("Starting MindSpore Training (High Accuracy Mode - 100k samples)...")
    # Increased Epochs
    model.train(epoch=10, train_dataset=dataset, callbacks=[LossMonitor(per_print_times=100)])
    
    # Evaluation
    print("\nEvaluating Model on Test Set...")
    # Manual batch inference for metrics
    test_tensor = Tensor(X_test)
    logits = net(test_tensor)
    preds = np.argmax(logits.asnumpy(), axis=1)
    
    # Calculate Metrics
    acc = np.mean(preds == y_test)
    
    # Precision/Recall/F1 (Macro Average)
    from sklearn.metrics import classification_report
    report = classification_report(y_test, preds, output_dict=True, zero_division=0)
    
    print(f"Accuracy: {acc:.2%}")
    print(f"Precision (Macro): {report['macro avg']['precision']:.2f}")
    print(f"Recall (Macro): {report['macro avg']['recall']:.2f}")
    print(f"F1 Score (Macro): {report['macro avg']['f1-score']:.2f}")
    
    # Save Checkpoint
    mindspore.save_checkpoint(net, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")

if __name__ == "__main__":
    train()
