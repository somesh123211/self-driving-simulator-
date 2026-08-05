import argparse
import base64
import io
import os
import time
import struct
import zlib
import numpy as np

import flask
from flask import request, jsonify, render_template, Response
import socketio
import eventlet
import eventlet.wsgi

# ---- SocketIO server (for Udacity Simulator on port 4567) ----
sio = socketio.Server(cors_allowed_origins='*')
app = flask.Flask(__name__, template_folder='templates', static_folder='static')

# ---------------------------------------------------------------
# Vehicle State
# ---------------------------------------------------------------
# Modes: 'STOP', 'FORWARD', 'REVERSE', 'MANUAL_LEFT', 'MANUAL_RIGHT'
current_mode = 'FORWARD'
last_voice_command = 'Auto Forward'

# Telemetry state - browser polls /api/status
telemetry_state = {
    'speed':    '0.0',
    'steering': '0.00',
    'throttle': '0.00',
    'mode':     'FORWARD'
}

# Latest camera frame from simulator (JPEG bytes)
latest_frame_bytes = None

# ---------------------------------------------------------------
# Tiny placeholder image (1x1 grey JPEG, no PIL needed)
# ---------------------------------------------------------------
def _make_placeholder():
    # Minimal 1x1 grey JPEG
    return bytes([
        0xFF,0xD8,0xFF,0xE0,0x00,0x10,0x4A,0x46,0x49,0x46,0x00,0x01,
        0x01,0x00,0x00,0x01,0x00,0x01,0x00,0x00,0xFF,0xDB,0x00,0x43,
        0x00,0x08,0x06,0x06,0x07,0x06,0x05,0x08,0x07,0x07,0x07,0x09,
        0x09,0x08,0x0A,0x0C,0x14,0x0D,0x0C,0x0B,0x0B,0x0C,0x19,0x12,
        0x13,0x0F,0x14,0x1D,0x1A,0x1F,0x1E,0x1D,0x1A,0x1C,0x1C,0x20,
        0x24,0x2E,0x27,0x20,0x22,0x2C,0x23,0x1C,0x1C,0x28,0x37,0x29,
        0x2C,0x30,0x31,0x34,0x34,0x34,0x1F,0x27,0x39,0x3D,0x38,0x32,
        0x3C,0x2E,0x33,0x34,0x32,0xFF,0xC0,0x00,0x0B,0x08,0x00,0x01,
        0x00,0x01,0x01,0x01,0x11,0x00,0xFF,0xC4,0x00,0x1F,0x00,0x00,
        0x01,0x05,0x01,0x01,0x01,0x01,0x01,0x01,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,
        0x09,0x0A,0x0B,0xFF,0xC4,0x00,0xB5,0x10,0x00,0x02,0x01,0x03,
        0x03,0x02,0x04,0x03,0x05,0x05,0x04,0x04,0x00,0x00,0x01,0x7D,
        0x01,0x02,0x03,0x00,0x04,0x11,0x05,0x12,0x21,0x31,0x41,0x06,
        0x13,0x51,0x61,0x07,0x22,0x71,0x14,0x32,0x81,0x91,0xA1,0x08,
        0x23,0x42,0xB1,0xC1,0x15,0x52,0xD1,0xF0,0x24,0x33,0x62,0x72,
        0x82,0x09,0x0A,0x16,0x17,0x18,0x19,0x1A,0x25,0x26,0x27,0x28,
        0x29,0x2A,0x34,0x35,0x36,0x37,0x38,0x39,0x3A,0x43,0x44,0x45,
        0x46,0x47,0x48,0x49,0x4A,0x53,0x54,0x55,0x56,0x57,0x58,0x59,
        0x5A,0x63,0x64,0x65,0x66,0x67,0x68,0x69,0x6A,0x73,0x74,0x75,
        0x76,0x77,0x78,0x79,0x7A,0x83,0x84,0x85,0x86,0x87,0x88,0x89,
        0x8A,0x92,0x93,0x94,0x95,0x96,0x97,0x98,0x99,0x9A,0xA2,0xA3,
        0xA4,0xA5,0xA6,0xA7,0xA8,0xA9,0xAA,0xB2,0xB3,0xB4,0xB5,0xB6,
        0xB7,0xB8,0xB9,0xBA,0xC2,0xC3,0xC4,0xC5,0xC6,0xC7,0xC8,0xC9,
        0xCA,0xD2,0xD3,0xD4,0xD5,0xD6,0xD7,0xD8,0xD9,0xDA,0xE1,0xE2,
        0xE3,0xE4,0xE5,0xE6,0xE7,0xE8,0xE9,0xEA,0xF1,0xF2,0xF3,0xF4,
        0xF5,0xF6,0xF7,0xF8,0xF9,0xFA,0xFF,0xDA,0x00,0x08,0x01,0x01,
        0x00,0x00,0x3F,0x00,0xFB,0xD2,0x8A,0x28,0x03,0xFF,0xD9
    ])

PLACEHOLDER_BYTES = _make_placeholder()


# ---------------------------------------------------------------
# Control values per mode (simple, no model)
# ---------------------------------------------------------------
def get_control():
    """Return (steering_angle, throttle) based on current_mode."""
    if current_mode == 'STOP':
        return 0.0, 0.0
    elif current_mode == 'FORWARD':
        return 0.0, 0.25        # straight, ~5 mph
    elif current_mode == 'REVERSE':
        return 0.0, -0.40       # straight reverse
    elif current_mode == 'MANUAL_LEFT':
        return -0.18, 0.25      # slight left (~10°) + forward speed
    elif current_mode == 'MANUAL_RIGHT':
        return 0.18, 0.25       # slight right (~10°) + forward speed
    return 0.0, 0.0


# ---------------------------------------------------------------
# Voice command parser
# ---------------------------------------------------------------
def parse_voice_command(text):
    global current_mode, last_voice_command
    text_lower = text.lower().strip()

    if any(k in text_lower for k in ['stop', 'halt', 'brake', 'freeze', 'hold', 'wait']):
        current_mode = 'STOP'
        msg = 'Car Stopped'
    elif any(k in text_lower for k in ['reverse', 'backward', 'backwards', 'back']):
        current_mode = 'REVERSE'
        msg = 'Reversing'
    elif any(k in text_lower for k in ['forward', 'drive', 'go', 'start', 'ahead', 'move']):
        current_mode = 'FORWARD'
        msg = 'Driving Forward at 5 mph'
    elif 'left' in text_lower:
        current_mode = 'MANUAL_LEFT'
        msg = 'Nudging Left (auto-returns)'
    elif 'right' in text_lower:
        current_mode = 'MANUAL_RIGHT'
        msg = 'Nudging Right (auto-returns)'
    else:
        msg = f'Unknown command: "{text}"'

    last_voice_command = msg
    telemetry_state['mode'] = current_mode
    print(f'[VOICE] "{text}" → {msg} (mode={current_mode})')
    return current_mode, msg


# ---------------------------------------------------------------
# SocketIO Events (Udacity Simulator)
# ---------------------------------------------------------------
@sio.on('telemetry')
def telemetry(sid, data):
    global latest_frame_bytes
    if data:
        current_speed = float(data.get('speed', 0))
        img_string = data.get('image', '')

        # Store latest frame for browser polling
        if img_string:
            latest_frame_bytes = base64.b64decode(img_string)

        # Get control values from current mode
        steering_angle, throttle = get_control()

        # Update telemetry state for browser polling
        telemetry_state['speed']    = f'{current_speed:.1f}'
        telemetry_state['steering'] = f'{steering_angle:.2f}'
        telemetry_state['throttle'] = f'{throttle:.2f}'
        telemetry_state['mode']     = current_mode

        send_control(steering_angle, throttle)


@sio.on('connect')
def connect(sid, environ):
    print(f'[INFO] Simulator connected (sid: {sid})')
    send_control(0, 0)


def send_control(steering_angle, throttle):
    sio.emit('steer', data={
        'steering_angle': str(steering_angle),
        'throttle':       str(throttle)
    })


# ---------------------------------------------------------------
# Flask HTTP Routes
# ---------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/latest_frame')
def latest_frame():
    frame = latest_frame_bytes if latest_frame_bytes is not None else PLACEHOLDER_BYTES
    return Response(frame, mimetype='image/jpeg', headers={
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    })


@app.route('/api/status')
def api_status():
    return jsonify(telemetry_state)


@app.route('/api/voice_command', methods=['POST'])
def api_voice_command():
    data = request.json or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'status': 'error', 'message': 'No text provided'}), 400
    mode, msg = parse_voice_command(text)
    return jsonify({'status': 'ok', 'transcript': text, 'mode': mode, 'message': msg})


@app.route('/api/set_mode', methods=['POST'])
def api_set_mode():
    global current_mode
    data = request.json or {}
    mode = data.get('mode', 'FORWARD').upper()
    # Map DRIVE → FORWARD for compatibility with JS nudge timer
    if mode == 'DRIVE':
        mode = 'FORWARD'
    allowed = ['FORWARD', 'STOP', 'REVERSE', 'MANUAL_LEFT', 'MANUAL_RIGHT']
    if mode in allowed:
        current_mode = mode
        telemetry_state['mode'] = current_mode
        print(f'[SET_MODE] → {current_mode}')
    return jsonify({'status': 'ok', 'mode': current_mode})


# ---------------------------------------------------------------
# Start Server
# ---------------------------------------------------------------
if __name__ == '__main__':
    print('=' * 60)
    print('  Udacity Simulator - Manual Voice Control')
    print('  Commands: "drive/forward" | "stop" | "reverse"')
    print('  Nudge:    "left" | "right"  (auto-returns in 1.5s)')
    print('=' * 60)
    print('[INFO] Server on port 4567 — Open: http://localhost:4567')

    app_middleware = socketio.Middleware(sio, app)
    eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 4567)), app_middleware)
