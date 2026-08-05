# Self-Driving Simulator — Voice + Terminal Control

A voice-controlled autonomous driving system for the **Udacity Self-Driving Car Simulator**.

## Features
- 🎙️ **Voice commands** via microphone (Google Speech Recognition)
- ⌨️ **Keyboard control** via terminal
- 🚗 **Speed-capped manual control** (max 10 mph)
- ⬅️➡️ **Nudge steering** — brief left/right adjustment, auto-returns to straight
- 🔁 **Reverse mode** with gear-engagement logic

## Quick Start

```powershell
# Install dependencies
.\venv\Scripts\python.exe -m pip install -r voice_command\requirements_voice.txt

# Run terminal + mic control
.\venv\Scripts\python.exe voice_command\drive_terminal.py
```

Then open the **Udacity Simulator** → Track 1 → **Autonomous Mode**

## Commands

| Say or Type | Action |
|-------------|--------|
| `forward` / `drive` / `go` | Drive straight at 10 mph |
| `stop` / `halt` | Stop the car |
| `reverse` / `back` | Go backward |
| `left` | Nudge left 1.5s → returns straight |
| `right` | Nudge right 1.5s → returns straight |
| `quit` | Exit |

## Project Structure

```
data reverse/
├── voice_command/
│   ├── drive_terminal.py   # Main script: terminal + mic control
│   ├── drive_voice.py      # Web UI version (Flask + HTTP polling)
│   ├── templates/          # HTML dashboard
│   ├── static/             # CSS + JS
│   └── requirements_voice.txt
├── train.py                # NVIDIA CNN model training
├── drive.py                # Original autonomous drive script
└── .gitignore
```

## Requirements
- Python 3.10
- PyAudio (for microphone)
- SpeechRecognition
- python-socketio 4.x + eventlet
- Udacity Self-Driving Car Simulator
