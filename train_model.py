import numpy as np
import pandas as pd
import mindspore as ms
from mindspore import nn, Tensor
from mindspore.dataset import NumpySlicesDataset

# Use PYNATIVE for Windows stability
ms.set_context(mode=ms.PYNATIVE_MODE)

CSV_PATH = "triage_data.csv"
CKPT_PATH = "triage_model.ckpt"

# -------------------------
# 1. Load dataset
# -------------------------
df = pd.read_csv(CSV_PATH)

X = df.drop(columns=["label"]).values.astype(np.float32)
y = df["label"].values.astype(np.int32)

# -------------------------
# 2. Train / test split
# -------------------------
split = int(0.8 * len(X))
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

train_ds = NumpySlicesDataset(
    {"x": X_train, "y": y_train},
    shuffle=True
).batch(64)

test_ds = NumpySlicesDataset(
    {"x": X_test, "y": y_test},
    shuffle=False
).batch(64)

# -------------------------
# 3. Define model
# -------------------------
class TriageNet(nn.Cell):
    def __init__(self):
        super().__init__()
        self.net = nn.SequentialCell(
            nn.Dense(11, 32),
            nn.ReLU(),
            nn.Dense(32, 16),
            nn.ReLU(),
            nn.Dense(16, 4)
        )

    def construct(self, x):
        return self.net(x)

net = TriageNet()

# -------------------------
# 4. Loss & optimizer
# -------------------------
loss_fn = nn.SoftmaxCrossEntropyWithLogits(
    sparse=True,
    reduction="mean"
)

optimizer = nn.Adam(
    net.trainable_params(),
    learning_rate=0.001
)

model = ms.Model(
    net,
    loss_fn=loss_fn,
    optimizer=optimizer,
    metrics={"acc": nn.Accuracy()}
)

# -------------------------
# 5. Train
# -------------------------
print("Training started...")
model.train(
    epoch=12,
    train_dataset=train_ds,
    dataset_sink_mode=False
)
print("Training finished.")

# -------------------------
# 6. Evaluate
# -------------------------
result = model.eval(
    test_ds,
    dataset_sink_mode=False
)
print("Evaluation result:", result)

# -------------------------
# 7. Save model
# -------------------------
ms.save_checkpoint(net, CKPT_PATH)
print("Model saved as:", CKPT_PATH)
