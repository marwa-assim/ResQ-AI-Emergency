import pandas as pd
import numpy as np
import os
import json
from sklearn.feature_extraction.text import CountVectorizer
import mindspore
import mindspore.nn as nn
from mindspore import Tensor, Model
from mindspore.train.callback import LossMonitor

DATA_DIR = r"data/mimic/mimic-iv-ed-2.2/ed"
TRIAGE_PATH = os.path.join(DATA_DIR, "triage.csv.gz")
MODEL_PATH = "mimic_risk_model_advanced.ckpt"
SCALING_PATH = "mindspore_scaling_advanced.json"
VOCAB_PATH = "mindspore_vocab.json"

NUM_COLS = ['temperature', 'heartrate', 'resprate', 'o2sat', 'sbp', 'dbp', 'pain']
NUM_CLASSES = 5
MAX_FEATURES = 50 # Top 50 clinical keywords

class HybridRiskModel(nn.Cell):
    def __init__(self, input_dim, hidden_dim=128, output_dim=5):
        super(HybridRiskModel, self).__init__()
        self.fc1 = nn.Dense(input_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(p=0.3)
        self.fc2 = nn.Dense(hidden_dim, int(hidden_dim/2)) 
        self.fc3 = nn.Dense(int(hidden_dim/2), output_dim)
        
    def construct(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.dropout(x)
        x = self.fc2(x)
        x = self.relu(x)
        x = self.fc3(x)
        return x

def preprocess_data():
    print("Loading MIMIC Data...")
    df = pd.read_csv(TRIAGE_PATH, compression='gzip')
    df = df.dropna(subset=['acuity'])
    df['acuity'] = df['acuity'].astype(int)
    
    # 1. Process Vitals
    for col in NUM_COLS:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    stats = {}
    for col in NUM_COLS:
        df[col] = df[col].fillna(df[col].median())
        mu = df[col].mean()
        sigma = df[col].std()
        if sigma == 0: sigma = 1
        df[col] = ((df[col] - mu) / sigma).clip(-5, 5)
        stats[col] = {'mean': float(mu), 'std': float(sigma)}
    
    X_num = df[NUM_COLS].values.astype(np.float32)
    
    # 2. Process NLP (Chief Complaint)
    df['chiefcomplaint'] = df['chiefcomplaint'].fillna("none").str.lower()
    vectorizer = CountVectorizer(max_features=MAX_FEATURES, stop_words='english', binary=True)
    X_text = vectorizer.fit_transform(df['chiefcomplaint']).toarray().astype(np.float32)
    
    # Save Vocab
    vocab = vectorizer.get_feature_names_out().tolist()
    with open(VOCAB_PATH, 'w') as f:
        json.dump(vocab, f)
        
    # Save Scaling Stats
    with open(SCALING_PATH, 'w') as f:
        json.dump(stats, f)

    # Combine Features
    X = np.hstack((X_num, X_text))
    y = df['acuity'].values - 1 # 0-indexed
    
    return X, y

def train():
    mindspore.set_device("CPU")
    X, y = preprocess_data()
    
    # Limit for training speed (Targeting high accuracy, so using 200k samples)
    if len(X) > 200000:
        indices = np.random.choice(len(X), 200000, replace=False)
        X = X[indices]
        y = y[indices]

    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    dataset = mindspore.dataset.NumpySlicesDataset({"data": X_train, "label": y_train}, shuffle=True)
    dataset = dataset.batch(128)
    
    net = HybridRiskModel(input_dim=X.shape[1], hidden_dim=128, output_dim=NUM_CLASSES)
    loss = nn.SoftmaxCrossEntropyWithLogits(sparse=True, reduction='mean')
    opt = nn.Adam(net.trainable_params(), learning_rate=0.001)
    
    model = Model(net, loss_fn=loss, optimizer=opt, metrics={'acc'})
    
    print("Starting MindSpore Hybrid Training (Vitals + NLP)...")
    model.train(epoch=15, train_dataset=dataset, callbacks=[LossMonitor(per_print_times=100)])
    
    print("\nEvaluating Model on Test Set...")
    test_tensor = Tensor(X_test)
    logits = net(test_tensor)
    preds = np.argmax(logits.asnumpy(), axis=1)
    
    acc = np.mean(preds == y_test)
    from sklearn.metrics import classification_report
    report = classification_report(y_test, preds, output_dict=True, zero_division=0)
    
    print(f"Accuracy: {acc:.2%}")
    print(f"Precision (Macro): {report['macro avg']['precision']:.2f}")
    print(f"Recall (Macro): {report['macro avg']['recall']:.2f}")
    print(f"F1 Score (Macro): {report['macro avg']['f1-score']:.2f}")
    
    mindspore.save_checkpoint(net, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")

if __name__ == "__main__":
    train()
