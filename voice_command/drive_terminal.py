"""
drive_terminal.py  â€”  Udacity Simulator Control via Terminal + Microphone
=========================================================================
Commands (type OR speak):
  forward / drive / go   â†’  straight forward at 5 mph
  stop / halt / brake    â†’  stop
  reverse / back         â†’  straight reverse
  left                   â†’  nudge left 1.5 s then return to forward
  right                  â†’  nudge right 1.5 s then return to forward
  quit / exit            â†’  quit
"""

import threading
import time
import base64
import sys

import socketio
import eventlet
import eventlet.wsgi

# â”€â”€ SocketIO server (Udacity Simulator connects here on port 4567) â”€â”€
sio = socketio.Server(cors_allowed_origins='*')

# â”€â”€ Vehicle State â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
current_mode = 'FORWARD'   # default: drive straight

MAX_SPEED = 10.0   # mph -- hard cap

# Steering angle per mode (throttle computed dynamically from live speed)
STEERING = {
    'FORWARD':      0.00,
    'STOP':         0.00,
    'REVERSE':      0.00,
    'MANUAL_LEFT':  -0.36,   # doubled sensitivity
    'MANUAL_RIGHT':  0.36,   # doubled sensitivity
}

def compute_throttle(mode, speed):
    """Return throttle value capped so car never exceeds MAX_SPEED."""
    if mode == 'STOP':
        return 0.0
    elif mode == 'REVERSE':
        # Udacity simulator needs a full -1.0 jolt when stationary
        # to engage reverse gear in Unity's CarController
        if speed < 0.5:
            return -1.0    # force reverse gear engagement
        elif speed < MAX_SPEED:
            return -0.40   # maintain reverse speed
        else:
            return 0.0     # at cap -- release
    else:
        # FORWARD / MANUAL_LEFT / MANUAL_RIGHT -- cap at MAX_SPEED
        if speed < MAX_SPEED - 1.0:
            return 0.35        # accelerate
        elif speed < MAX_SPEED:
            return 0.15        # coast gently to cap
        else:
            return 0.0         # at or above cap -- release throttle

_nudge_thread = None


def set_mode(mode, silent=False):
    """Update current_mode and print status line."""
    global current_mode
    current_mode = mode
    steer = STEERING.get(mode, 0.0)
    if not silent:
        print(f'\n  â–¶  MODE â†’ {mode:<14}  steer={steer:+.2f}  max_speed={MAX_SPEED:.0f} mph')


def nudge(direction):
    """Apply a brief left/right nudge then return to FORWARD."""
    global _nudge_thread
    mode = 'MANUAL_LEFT' if direction == 'left' else 'MANUAL_RIGHT'
    set_mode(mode)
    emoji = 'â¬…' if direction == 'left' else 'âž¡'
    print(f'  {emoji}  Nudging {direction}... returns to FORWARD in 1.5 s')

    def _return():
        time.sleep(1.5)
        set_mode('FORWARD')
        print('  â†©  Back to straight FORWARD')

    _nudge_thread = threading.Thread(target=_return, daemon=True)
    _nudge_thread.start()


def parse_command(text):
    """Map text to a mode action."""
    t = text.lower().strip()
    if not t:
        return
    if any(k in t for k in ('stop', 'halt', 'brake', 'freeze', 'wait')):
        set_mode('STOP')
    elif any(k in t for k in ('reverse', 'backward', 'back', 'backwards')):
        set_mode('REVERSE')
    elif any(k in t for k in ('forward', 'drive', 'go', 'start', 'ahead', 'move')):
        set_mode('FORWARD')
    elif 'left' in t:
        nudge('left')
    elif 'right' in t:
        nudge('right')
    elif t in ('quit', 'exit', 'q'):
        print('  Goodbye!')
        import os; os._exit(0)
    else:
        print(f'  [?] Unknown command: "{text}"')
        print('      Try: forward | stop | reverse | left | right | quit')


# â”€â”€ SocketIO telemetry handler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@sio.on('telemetry')
def telemetry(sid, data):
    if data:
        speed = float(data.get('speed', 0))
        steer    = STEERING.get(current_mode, 0.0)
        throttle = compute_throttle(current_mode, speed)
        # Print live status on same line
        print(f'\r  [CAR] speed={speed:5.1f}/{MAX_SPEED:.0f} mph  steer={steer:+.2f}  '
              f'throttle={throttle:+.2f}  mode={current_mode:<14}', end='', flush=True)
        sio.emit('steer', data={
            'steering_angle': str(steer),
            'throttle':       str(throttle)
        })


@sio.on('connect')
def connect(sid, environ):
    print('\n  [âœ“] Simulator connected â€” ready for commands!')
    sio.emit('steer', data={'steering_angle': '0', 'throttle': '0'})


# â”€â”€ Keyboard input thread â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def keyboard_thread():
    print('\n' + '='*60)
    print('  KEYBOARD COMMANDS')
    print('  Type: forward | stop | reverse | left | right | quit')
    print('='*60)
    while True:
        try:
            cmd = input('\n  keyboard> ').strip()
            parse_command(cmd)
        except (EOFError, KeyboardInterrupt):
            break


# â”€â”€ Microphone input thread â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def mic_thread():
    try:
        import speech_recognition as sr
        r   = sr.Recognizer()
        r.pause_threshold        = 0.6   # stop listening after 0.6s silence
        r.dynamic_energy_threshold = True

        # Use default mic (device_index=None avoids listing device names
        # which can crash on Windows with non-ASCII characters in device names)
        mic = sr.Microphone(device_index=None)
        print('\n  [MIC] Calibrating microphone for ambient noise...')
        with mic as source:
            r.adjust_for_ambient_noise(source, duration=1.5)
        print('  [MIC] Microphone ready - speak anytime!')
        print('  [MIC] Say: "forward" | "stop" | "reverse" | "left" | "right"\n')

        while True:
            try:
                with mic as source:
                    audio = r.listen(source, timeout=8, phrase_time_limit=5)
                # Recognize speech
                text = r.recognize_google(audio)
                print(f'\n  [MIC] Heard: "{text}"')
                parse_command(text)
            except sr.WaitTimeoutError:
                pass   # silence â€” just keep listening
            except sr.UnknownValueError:
                pass   # couldn't understand â€” ignore
            except sr.RequestError as e:
                print(f'\n  [MIC] Google API error: {e}')
                time.sleep(2)
            except Exception as e:
                print(f'\n  [MIC] Error: {e}')
                time.sleep(1)

    except ImportError:
        print('\n  [MIC] SpeechRecognition not installed â€” keyboard only.')
    except OSError as e:
        print(f'\n  [MIC] No microphone found: {e}')
        print('         Keyboard input still works.')
    except Exception as e:
        print(f'\n  [MIC] Mic init failed: {e}')


# â”€â”€ Main â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == '__main__':
    print('\n' + '='*60)
    print('  Udacity Simulator â€” Terminal + Mic Control')
    print('  Port: 4567  |  Default: FORWARD (5 mph straight)')
    print('='*60)

    # Start keyboard thread
    threading.Thread(target=keyboard_thread, daemon=True).start()

    # Start microphone thread
    threading.Thread(target=mic_thread, daemon=True).start()

    # Start SocketIO server (blocks â€” this is the main loop)
    print('\n  [INFO] Waiting for Udacity Simulator to connect...')
    print('         Open simulator â†’ Track 1 â†’ Autonomous Mode\n')

    app_wsgi = socketio.Middleware(sio)
    eventlet.wsgi.server(
        eventlet.listen(('0.0.0.0', 4567)),
        app_wsgi,
        log_output=False   # suppress noisy HTTP logs
    )

