import numpy as np
import csv
import mindspore as ms
from mindspore import nn, Tensor, context, ops

# Set Context (CPU for broad compatibility, can switch to GPU/Ascend)
context.set_context(mode=context.PYNATIVE_MODE, device_target="CPU")

# ----------------------------
# 1. Pipeline Definition
# ----------------------------
class TriageDataset:
    def __init__(self, csv_file):
        self.features = []
        self.labels = []
        
        with open(csv_file, 'r') as f:
            reader = csv.reader(f)
            header = next(reader) # Skip header
            # Header: age,arrival_mode,heart_rate,spo2,temperature,chest_pain,breathing_difficulty,bleeding,fainting,chronic_disease,allergy_risk,label
            
            for row in reader:
                # Parse Features (First 11 cols)
                feats = [float(x) for x in row[:11]]
                # Parse Label (Last col)
                label = int(row[11])
                
                # Normalize key continuous vars (Age, HR, SpO2, Temp)
                # Simple Min-Max scaling based on medical norms for stability
                # Age (0-100), HR (40-200), SpO2 (70-100), Temp (35-42)
                feats[0] = feats[0] / 100.0
                feats[2] = (feats[2] - 40) / 160.0
                feats[3] = (feats[3] - 70) / 30.0
                feats[4] = (feats[4] - 35) / 7.0
                
                self.features.append(feats)
                self.labels.append(label)
                
        self.features = np.array(self.features, dtype=np.float32)
        self.labels = np.array(self.labels, dtype=np.int32)
        
    def __getitem__(self, index):
        return self.features[index], self.labels[index]
        
    def __len__(self):
        return len(self.labels)

# ----------------------------
# 2. Model Definition
# ----------------------------
class TriageNet(nn.Cell):
    def __init__(self):
        super(TriageNet, self).__init__()
        # 11 Input Features -> Hidden 64 -> Hidden 32 -> 4 Classes (Priority 0,1,2,3)
        self.dense1 = nn.Dense(11, 64)
        self.relu1 = nn.ReLU()
        self.dense2 = nn.Dense(64, 32)
        self.relu2 = nn.ReLU()
        self.dense3 = nn.Dense(32, 4) 
        
    def construct(self, x):
        x = self.dense1(x)
        x = self.relu1(x)
        x = self.dense2(x)
        x = self.relu2(x)
        x = self.dense3(x)
        return x

# ----------------------------
# 3. Training Loop
# ----------------------------
def train_model():
    print("Loading Dataset...")
    dataset_generator = TriageDataset('triage_data.csv')
    
    # Check split
    train_size = int(0.8 * len(dataset_generator))
    print(f"Total Samples: {len(dataset_generator)} | Training on: {train_size}")
    
    # Create Batches (Manual simple batching for pure python/numpy simplicity in this script)
    # Using MindSpore Dataset API is better for large scale, but for 5000 rows, this is instant and reliable
    features = dataset_generator.features
    labels = dataset_generator.labels
    
    net = TriageNet()
    loss_fn = nn.SoftmaxCrossEntropyWithLogits(sparse=True, reduction='mean')
    optimizer = nn.Adam(net.trainable_params(), learning_rate=0.01)
    
    # Define Forward Function
    def forward_fn(data, label):
        logits = net(data)
        loss = loss_fn(logits, label)
        return loss, logits
    
    # Define Gradient Function
    grad_fn = ms.value_and_grad(forward_fn, None, optimizer.parameters, has_aux=True)
    
    # Train Step
    def train_step(data, label):
        (loss, _), grads = grad_fn(data, label)
        optimizer(grads)
        return loss

    print("Starting Training...")
    net.set_train()
    
    epochs = 20 # Fast training
    batch_size = 32
    
    for epoch in range(epochs):
        # Shuffle
        indices = np.random.permutation(len(features))
        features = features[indices]
        labels = labels[indices]
        
        total_loss = 0
        steps = 0
        
        for i in range(0, len(features), batch_size):
            batch_x = Tensor(features[i:i+batch_size], ms.float32)
            batch_y = Tensor(labels[i:i+batch_size], ms.int32)
            
            loss = train_step(batch_x, batch_y)
            total_loss += float(loss)
            steps += 1
            
        print(f"Epoch {epoch+1}/{epochs} - Avg Loss: {total_loss/steps:.4f}")

    print("Training Complete. Saving Model...")
    ms.save_checkpoint(net, "triage_model.ckpt")
    print("Model saved to triage_model.ckpt")

if __name__ == "__main__":
    train_model()
