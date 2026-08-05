import os
import cv2
import csv
import random
import numpy as np
from sklearn.model_selection import train_test_split

DATA_DIR = os.path.join(os.getcwd(), 'data_reverse_track1')
CSV_PATH = os.path.join(DATA_DIR, 'driving_log.csv')
IMG_DIR = os.path.join(DATA_DIR, 'IMG')

print(f"[INFO] Loading dataset from: {CSV_PATH}")

# 1. Parse CSV driving log
samples = []
with open(CSV_PATH, 'r') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        if len(row) >= 4:
            samples.append(row)

print(f"[INFO] Total driving records: {len(samples)}")

# 2. Extract Center, Left, Right images with recovery steering corrections
image_paths = []
steering_angles = []
STEERING_CORRECTION = 0.22

for sample in samples:
    center_name = os.path.basename(sample[0].strip())
    left_name = os.path.basename(sample[1].strip())
    right_name = os.path.basename(sample[2].strip())
    
    center_path = os.path.join(IMG_DIR, center_name)
    left_path = os.path.join(IMG_DIR, left_name)
    right_path = os.path.join(IMG_DIR, right_name)
    
    steering = float(sample[3])
    
    if os.path.exists(center_path):
        image_paths.append(center_path)
        steering_angles.append(steering)
    if os.path.exists(left_path):
        image_paths.append(left_path)
        steering_angles.append(steering + STEERING_CORRECTION)
    if os.path.exists(right_path):
        image_paths.append(right_path)
        steering_angles.append(steering - STEERING_CORRECTION)

print(f"[INFO] Total valid image samples: {len(image_paths)}")

train_paths, val_paths, train_angles, val_angles = train_test_split(
    image_paths, steering_angles, test_size=0.2, random_state=42, shuffle=True
)

print(f"[INFO] Training set: {len(train_paths)} | Validation set: {len(val_paths)}")

def preprocess_image(img):
    """Crop top 60px sky and bottom 25px hood, resize to 200x66, normalize to [-0.5, 0.5]"""
    cropped = img[60:135, :, :]
    resized = cv2.resize(cropped, (200, 66), interpolation=cv2.INTER_AREA)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    normalized = (rgb.astype(np.float32) / 255.0) - 0.5
    return normalized

def augment_data(img, steering):
    """Augmentation: random horizontal flip, brightness adjustment, random translation"""
    if random.random() > 0.5:
        img = cv2.flip(img, 1)
        steering = -steering

    if random.random() > 0.5:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        ratio = 0.4 + random.uniform(0, 0.8)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * ratio, 0, 255).astype(np.uint8)
        img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    if random.random() > 0.5:
        dx = random.randint(-15, 15)
        dy = random.randint(-10, 10)
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        img = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]))
        steering += dx * 0.002

    return img, steering

# Detect PyTorch or TensorFlow
USE_TORCH = False
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    USE_TORCH = True
    print("[INFO] PyTorch detected. Using PyTorch training backend.")
except ImportError:
    try:
        import tensorflow as tf
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import Conv2D, Flatten, Dense, Dropout
        from tensorflow.keras.optimizers import Adam
        from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping
        print("[INFO] TensorFlow detected. Using Keras training backend.")
    except ImportError:
        raise ImportError("Neither PyTorch nor TensorFlow is installed! Run `pip install torch` or `pip install tensorflow`.")

if USE_TORCH:
    class NvidiaPyTorchCNN(nn.Module):
        """NVIDIA End-to-End Deep Learning Model in PyTorch"""
        def __init__(self):
            super(NvidiaPyTorchCNN, self).__init__()
            self.conv_layers = nn.Sequential(
                nn.Conv2d(3, 24, kernel_size=5, stride=2),
                nn.ELU(),
                nn.Conv2d(24, 36, kernel_size=5, stride=2),
                nn.ELU(),
                nn.Conv2d(36, 48, kernel_size=5, stride=2),
                nn.ELU(),
                nn.Conv2d(48, 64, kernel_size=3, stride=1),
                nn.ELU(),
                nn.Conv2d(64, 64, kernel_size=3, stride=1),
                nn.ELU(),
                nn.Dropout(0.3)
            )
            self.fc_layers = nn.Sequential(
                nn.Linear(64 * 1 * 18, 100),
                nn.ELU(),
                nn.Dropout(0.3),
                nn.Linear(100, 50),
                nn.ELU(),
                nn.Dropout(0.2),
                nn.Linear(50, 10),
                nn.ELU(),
                nn.Linear(10, 1)
            )

        def forward(self, x):
            x = self.conv_layers(x)
            x = x.view(x.size(0), -1)
            x = self.fc_layers(x)
            return x

    class DrivingDataset(Dataset):
        def __init__(self, paths, angles, is_training=True):
            self.paths = paths
            self.angles = angles
            self.is_training = is_training

        def __len__(self):
            return len(self.paths)

        def __getitem__(self, idx):
            path = self.paths[idx]
            steering = self.angles[idx]
            img = cv2.imread(path)
            if img is None:
                img = np.zeros((160, 320, 3), dtype=np.uint8)

            if self.is_training:
                img, steering = augment_data(img, steering)

            proc = preprocess_image(img)
            tensor_img = torch.tensor(proc, dtype=torch.float32).permute(2, 0, 1)
            tensor_steering = torch.tensor([steering], dtype=torch.float32)
            return tensor_img, tensor_steering

    def train_pytorch():
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"[INFO] PyTorch computation device: {device}")

        train_ds = DrivingDataset(train_paths, train_angles, is_training=True)
        val_ds = DrivingDataset(val_paths, val_angles, is_training=False)

        train_loader = DataLoader(train_ds, batch_size=128, shuffle=True, num_workers=0)
        val_loader = DataLoader(val_ds, batch_size=128, shuffle=False, num_workers=0)

        model = NvidiaPyTorchCNN().to(device)
        criterion = nn.MSELoss()
        optimizer = optim.Adam(model.parameters(), lr=1e-4)

        best_val_loss = float('inf')
        EPOCHS = 20

        print(f"\n--- Starting {EPOCHS} Epoch Training ---")
        for epoch in range(1, EPOCHS + 1):
            model.train()
            train_loss = 0.0
            for imgs, target in train_loader:
                imgs, target = imgs.to(device), target.to(device)
                optimizer.zero_grad()
                output = model(imgs)
                loss = criterion(output, target)
                loss.backward()
                optimizer.step()
                train_loss += loss.item() * imgs.size(0)

            train_loss /= len(train_loader.dataset)

            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for imgs, target in val_loader:
                    imgs, target = imgs.to(device), target.to(device)
                    output = model(imgs)
                    loss = criterion(output, target)
                    val_loss += loss.item() * imgs.size(0)

            val_loss /= len(val_loader.dataset)

            print(f"Epoch [{epoch:02d}/{EPOCHS:02d}] - Train Loss: {train_loss:.5f} | Val Loss: {val_loss:.5f}")

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save(model.state_dict(), 'best_model.pth')
                print(f"  --> Saved new best model to 'best_model.pth' (Val Loss: {val_loss:.5f})")

        print("\n[SUCCESS] Training finished! Best model saved to 'best_model.pth'")

else:
    class KerasGenerator(tf.keras.utils.Sequence):
        def __init__(self, paths, angles, batch_size=128, is_training=True):
            self.paths = paths
            self.angles = angles
            self.batch_size = batch_size
            self.is_training = is_training
            self.indices = np.arange(len(self.paths))

        def __len__(self):
            return int(np.floor(len(self.paths) / self.batch_size))

        def __getitem__(self, index):
            batch_idx = self.indices[index * self.batch_size:(index + 1) * self.batch_size]
            imgs, st = [], []
            for idx in batch_idx:
                img = cv2.imread(self.paths[idx])
                s = self.angles[idx]
                if self.is_training and img is not None:
                    img, s = augment_data(img, s)
                if img is not None:
                    imgs.append(preprocess_image(img))
                    st.append(s)
            return np.array(imgs, dtype=np.float32), np.array(st, dtype=np.float32)

        def on_epoch_end(self):
            if self.is_training:
                np.random.shuffle(self.indices)

    def train_keras():
        model = Sequential([
            Conv2D(24, (5, 5), strides=(2, 2), activation='elu', input_shape=(66, 200, 3)),
            Conv2D(36, (5, 5), strides=(2, 2), activation='elu'),
            Conv2D(48, (5, 5), strides=(2, 2), activation='elu'),
            Conv2D(64, (3, 3), activation='elu'),
            Conv2D(64, (3, 3), activation='elu'),
            Dropout(0.3),
            Flatten(),
            Dense(100, activation='elu'),
            Dropout(0.3),
            Dense(50, activation='elu'),
            Dropout(0.2),
            Dense(10, activation='elu'),
            Dense(1)
        ])
        model.compile(optimizer=Adam(learning_rate=1e-4), loss='mse')

        train_gen = KerasGenerator(train_paths, train_angles, batch_size=128, is_training=True)
        val_gen = KerasGenerator(val_paths, val_angles, batch_size=128, is_training=False)

        callbacks = [
            ModelCheckpoint('best_model.keras', monitor='val_loss', save_best_only=True, verbose=1),
            ModelCheckpoint('track 2part 2.keras', monitor='val_loss', save_best_only=True, verbose=0),
            EarlyStopping(monitor='val_loss', patience=7, restore_best_weights=True)
        ]

        print(f"\n--- Starting 20 Epoch Keras/TF Training ---")
        model.fit(train_gen, validation_data=val_gen, epochs=20, callbacks=callbacks, verbose=1)
        model.save('best_model.keras')
        print("[SUCCESS] Training finished! Best model saved to 'best_model.keras'")

if __name__ == '__main__':
    if USE_TORCH:
        train_pytorch()
    else:
        train_keras()
