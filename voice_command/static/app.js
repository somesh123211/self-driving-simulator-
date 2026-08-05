// Voice Command Web App - Pure HTTP Polling (NO SocketIO from browser!)
// Commands: "forward" | "stop" | "reverse" | "left" nudge | "right" nudge

// UI Elements
const cameraFeed = document.getElementById('cameraFeed');
const speedVal   = document.getElementById('speedVal');
const steerVal   = document.getElementById('steerVal');
const modeBadge  = document.getElementById('modeBadge');
const micBtn     = document.getElementById('micBtn');
const voiceStatusText = document.getElementById('voiceStatusText');

let nudgeTimer = null;

// ---- Live video: poll /latest_frame every 80ms ----
function updateFrame() {
    const img = new Image();
    img.onload = function() { cameraFeed.src = this.src; };
    img.src = '/latest_frame?t=' + Date.now();
}
setInterval(updateFrame, 80);

// ---- Telemetry: poll /api/status every 250ms ----
function updateTelemetry() {
    fetch('/api/status')
        .then(r => r.json())
        .then(data => {
            speedVal.textContent = data.speed    || '0.0';
            steerVal.textContent = data.steering || '0.00';
            const mode = data.mode || 'FORWARD';
            modeBadge.textContent = 'MODE: ' + mode;
            updateBadgeStyle(mode);
        })
        .catch(() => {});
}
setInterval(updateTelemetry, 250);

function updateBadgeStyle(mode) {
    if (mode === 'STOP') {
        modeBadge.style.borderColor = '#ef4444';
        modeBadge.style.color       = '#ef4444';
        modeBadge.style.background  = 'rgba(239, 68, 68, 0.2)';
    } else if (mode === 'REVERSE') {
        modeBadge.style.borderColor = '#9d50bb';
        modeBadge.style.color       = '#9d50bb';
        modeBadge.style.background  = 'rgba(157, 80, 187, 0.2)';
    } else if (mode === 'MANUAL_LEFT' || mode === 'MANUAL_RIGHT') {
        modeBadge.style.borderColor = '#f59e0b';
        modeBadge.style.color       = '#f59e0b';
        modeBadge.style.background  = 'rgba(245, 158, 11, 0.2)';
    } else {
        modeBadge.style.borderColor = '#00f2fe';
        modeBadge.style.color       = '#00f2fe';
        modeBadge.style.background  = 'rgba(0, 242, 254, 0.1)';
    }
}

// ---- NUDGE: steer slightly for 1.5s then return to FORWARD ----
function nudge(direction) {
    if (nudgeTimer) clearTimeout(nudgeTimer);
    const mode  = direction === 'left' ? 'MANUAL_LEFT' : 'MANUAL_RIGHT';
    const emoji = direction === 'left' ? '⬅️' : '➡️';
    voiceStatusText.textContent = emoji + ' Nudging ' + direction + '... (returns straight in 1.5s)';

    fetch('/api/set_mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: mode })
    });

    nudgeTimer = setTimeout(() => {
        fetch('/api/set_mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: 'FORWARD' })
        });
        voiceStatusText.textContent = '↩️ Back to straight forward';
        nudgeTimer = null;
    }, 1500);
}

// ---- Manual mode buttons ----
function setMode(mode) {
    if (nudgeTimer) { clearTimeout(nudgeTimer); nudgeTimer = null; }
    fetch('/api/set_mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: mode })
    })
    .then(res => res.json())
    .then(data => {
        const labels = {
            STOP:    '🛑 Car Stopped',
            FORWARD: '🚗 Driving Forward at 5 mph',
            REVERSE: '⏪ Reversing'
        };
        voiceStatusText.textContent = labels[data.mode] || ('Mode: ' + data.mode);
    });
}

// ---- Voice command via text ----
function sendVoiceCommand(text) {
    voiceStatusText.textContent = 'Processing: "' + text + '"...';
    fetch('/api/voice_command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text })
    })
    .then(res => res.json())
    .then(data => {
        voiceStatusText.textContent = '✅ "' + data.transcript + '" → ' + data.message;
        if (data.mode === 'MANUAL_LEFT')  nudge('left');
        else if (data.mode === 'MANUAL_RIGHT') nudge('right');
    })
    .catch(err => console.error('Error:', err));
}

// ---- Web Speech API (microphone) ----
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous     = false;
    recognition.interimResults = false;
    recognition.lang           = 'en-US';

    recognition.onstart = () => {
        micBtn.classList.add('listening');
        voiceStatusText.textContent = '🎙️ Listening... say "Forward", "Stop", "Reverse", "Left", or "Right"';
    };

    recognition.onresult = (event) => {
        sendVoiceCommand(event.results[0][0].transcript);
    };

    recognition.onerror = (event) => {
        micBtn.classList.remove('listening');
        if (event.error === 'not-allowed') {
            voiceStatusText.textContent = '⚠️ Click 🔒 in URL bar → Microphone → Allow, then click mic again';
        } else {
            voiceStatusText.textContent = 'Mic error: ' + event.error + '. Use chips below.';
        }
    };

    recognition.onend = () => micBtn.classList.remove('listening');

    micBtn.addEventListener('click', () => {
        if (micBtn.classList.contains('listening')) {
            recognition.stop();
        } else {
            try { recognition.start(); }
            catch(e) { voiceStatusText.textContent = 'Allow microphone access first.'; }
        }
    });
} else {
    voiceStatusText.textContent = 'Speech not supported. Use Chrome or Edge browser.';
    if (micBtn) { micBtn.style.opacity = '0.4'; micBtn.style.cursor = 'not-allowed'; }
}
