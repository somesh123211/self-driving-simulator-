import argparse
import base64
import io
import os
import sys
import time
import numpy as np
import cv2
from PIL import Image
import flask
import socketio
import eventlet
import eventlet.wsgi

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

sio = socketio.Server()
app = flask.Flask(__name__)
model = None
model_type = None  # 'pytorch' or 'keras'

# Track standstill time to force reverse gear shift in Unity CarController
standstill_start_time = None

# PyTorch Model Definition
USE_TORCH = False
try:
    import torch
    import torch.nn as nn
    USE_TORCH = True

    class NvidiaPyTorchCNN(nn.Module):
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
except ImportError:
    pass

def preprocess_image(pil_img):
    """
    Preprocess frame from Udacity Simulator:
    1. Convert PIL Image to RGB numpy array
    2. Crop sky/hood: [60:135, :, :]
    3. Resize to 200x66
    4. Normalize pixel values to [-0.5, 0.5]
    """
    img_arr = np.asarray(pil_img)
    if img_arr.shape[2] == 4:
        img_arr = cv2.cvtColor(img_arr, cv2.COLOR_RGBA2RGB)
    
    cropped = img_arr[60:135, :, :]
    resized = cv2.resize(cropped, (200, 66), interpolation=cv2.INTER_AREA)
    normalized = (resized.astype(np.float32) / 255.0) - 0.5
    return normalized

def predict_steering(image_np):
    global model, model_type
    if model_type == 'pytorch':
        tensor_img = torch.tensor(image_np, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0)
        with torch.no_grad():
            steering = model(tensor_img).item()
        return steering
    else:
        tensor_img = np.expand_dims(image_np, axis=0)
        steering = float(model.predict(tensor_img, verbose=0)[0][0])
        return steering

@sio.on('telemetry')
def telemetry(sid, data):
    global standstill_start_time
    if data:
        current_speed = float(data["speed"])
        current_steering = float(data["steering_angle"])
        img_string = data["image"]
        
        # Decode base64 image frame
        image = Image.open(io.BytesIO(base64.b64decode(img_string)))
        
        # Preprocess frame
        processed_frame = preprocess_image(image)
        
        # Predict steering angle from trained model
        steering_angle = predict_steering(processed_frame)
        steering_angle = float(np.clip(steering_angle, -1.0, 1.0))
        
        # Track speed for Reverse Gear engagement
        now = time.time()
        if current_speed < 0.2:
            if standstill_start_time is None:
                standstill_start_time = now
        else:
            standstill_start_time = None

        # Target reverse speed (12-15 mph)
        turn_severity = abs(steering_angle)
        if turn_severity > 0.35:
            target_speed = 10.0
        elif turn_severity > 0.20:
            target_speed = 13.0
        else:
            target_speed = 15.0

        # REVERSE DRIVING THROTTLE LOGIC:
        # In Unity CarController, negative throttle (-0.5 to -1.0) drives the car in REVERSE.
        # If stopped (speed < 0.2), send full reverse throttle (-1.0) to shift into Reverse Gear immediately!
        if standstill_start_time is not None:
            throttle = -1.0  # Full Reverse Acceleration to force Reverse Gear shift
        elif current_speed < target_speed:
            throttle = -0.50  # Reverse acceleration
        elif current_speed > target_speed + 2.0:
            throttle = 0.0    # Release throttle
        else:
            throttle = -0.25  # Reverse cruise maintenance

        print(f"[REVERSE MODE] Steer: {steering_angle:+.4f} | Speed: {current_speed:5.1f} mph | Throttle: {throttle:+.2f}")
        send_control(steering_angle, throttle)
    else:
        sio.emit('manual', data={}, skip_sid=True)

@sio.on('connect')
def connect(sid, environ):
    global standstill_start_time
    standstill_start_time = time.time()
    print(f"[INFO] Udacity Simulator Connected (sid: {sid})")
    send_control(0, -1.0)  # Initial Reverse pulse

def send_control(steering_angle, throttle):
    sio.emit(
        "steer",
        data={
            'steering_angle': steering_angle.__str__(),
            'throttle': throttle.__str__(),
            'brake': '0'
        },
        skip_sid=True
    )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Udacity Self-Driving Car Telemetry Server')
    parser.add_argument('model', type=str, nargs='?', default=None, help='Path to model file (.pth or .keras/.h5)')
    args = parser.parse_args()

    model_path = args.model
    if not model_path:
        if os.path.exists('best_model.pth'):
            model_path = 'best_model.pth'
        elif os.path.exists('best_model.keras'):
            model_path = 'best_model.keras'
        elif os.path.exists('track 2part 2.keras'):
            model_path = 'track 2part 2.keras'

    if not model_path or not os.path.exists(model_path):
        print(f"[ERROR] No model file found! Please train the model first using `python train.py`.")
        sys.exit(1)

    print(f"[INFO] Loading model weights from: {model_path}")
    if model_path.endswith('.pth') and USE_TORCH:
        model = NvidiaPyTorchCNN()
        model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
        model.eval()
        model_type = 'pytorch'
        print("[SUCCESS] Loaded PyTorch NVIDIA CNN model!")
    else:
        import tensorflow as tf
        model = tf.keras.models.load_model(model_path)
        model_type = 'keras'
        print("[SUCCESS] Loaded Keras/TensorFlow NVIDIA CNN model!")

    app = socketio.WSGIApp(sio, app)
    print("[INFO] Starting Reverse Telemetry Server on http://localhost:4567...")
    eventlet.wsgi.server(eventlet.listen(('', 4567)), app)
