#!/usr/bin/env python3
"""
YTMP3-DL Web Terminal Server – OLED Black Edition
Auto-deletes files after download. Secure streaming + download endpoints.
Suppresses backend warnings.
Now with automatic Cloudflare Tunnel and a nicer play/pause button.
"""

import warnings
warnings.filterwarnings("ignore", message=".*RequestsDependencyWarning.*")
warnings.filterwarnings("ignore", message=".*urllib3.*")
warnings.filterwarnings("ignore", message=".*chardet.*")

from flask import Flask, render_template_string, request, jsonify, send_file, abort
from flask_socketio import SocketIO, emit
import subprocess
import threading
import os
import time
import re
import traceback
import atexit
import signal
import sys

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ytmp3-dl-secret-key-2026'
socketio = SocketIO(app, cors_allowed_origins="*")

# Output directory (where mp3.py saves files)
default_path = os.getenv('OUTPUT_DIR', '~/ytmp3-premium/music-output')
OUTPUT_DIR = os.path.expanduser(default_path)

# Active processes
active_processes = {}

# ----------------------------------------------------------------------
# HTML Template – OLED Black, refined UI, custom download button
# (play/pause button now uses SVG icons, no emoji offset)
# ----------------------------------------------------------------------
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YTMP3-DL · OLED Terminal</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.5.4/socket.io.js"></script>
    <style>
               /* OLED Black Theme – Refined, better readability */
        :root {
            --bg: #000000;
            --card-bg: rgba(20, 20, 20, 0.7);
            --card-border: rgba(80, 80, 80, 0.3);
            --card-shadow: rgba(0, 0, 0, 0.95);
            --input-bg: rgba(30, 30, 30, 0.8);
            --input-border: rgba(100, 100, 100, 0.3);
            --text-primary: #ffffff;
            --text-secondary: #cccccc;
            --accent: #00ff88;
            --accent-glow: 0 0 15px rgba(0, 255, 136, 0.3);
            --btn-bg: #0a0a0a;
            --btn-hover: #1a1a1a;
            --terminal-bg: #0a0a0a;
            --terminal-text: #aaffaa;
            --scrollbar-track: #0a0a0a;
            --scrollbar-thumb: #2a2a2a;
            --blur: 30px;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        html {
            scroll-behavior: smooth;
        }

        body {
            background: var(--bg);
            color: var(--text-primary);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-weight: 400;
            min-height: 100vh;
            display: block;
            padding: 20px;
            position: relative;
        }

        .container {
            max-width: 1200px;
            width: 100%;
            margin: 0 auto;
            position: relative;
            z-index: 10;
        }

        /* Glass card with glow */
        .glass {
            background: var(--card-bg);
            backdrop-filter: blur(var(--blur));
            -webkit-backdrop-filter: blur(var(--blur));
            border: 1px solid var(--card-border);
            border-radius: 28px;
            box-shadow: 0 20px 40px var(--card-shadow), 0 0 0 1px rgba(255,255,255,0.02) inset;
            transition: all 0.3s ease;
        }

        .glass:hover {
            border-color: rgba(120, 120, 120, 0.5);
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.8), var(--accent-glow);
        }

        /* Header / Logo */
        .header {
            text-align: center;
            margin-bottom: 40px;
            animation: fadeInDown 0.6s ease-out;
        }

        .logo {
            font-size: 3.5rem;
            font-weight: 300;
            letter-spacing: 4px;
            background: linear-gradient(135deg, #606060 0%, #808080 25%, #a0a0a0 50%, #808080 75%, #606060 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
            filter: drop-shadow(0 0 10px rgba(255,255,255,0.1));
        }

        .tagline {
            font-size: 0.85rem;
            color: var(--text-secondary);
            letter-spacing: 2px;
            text-transform: uppercase;
        }

        /* Input card */
        .input-card {
            padding: 30px;
            margin-bottom: 30px;
            animation: fadeInUp 0.6s ease-out 0.1s both;
        }

        .input-label {
            display: block;
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .input-wrapper {
            display: flex;
            gap: 12px;
            align-items: center;
        }

        #urlInput {
            flex: 1;
            background: var(--input-bg);
            border: 1px solid var(--input-border);
            border-radius: 18px;
            padding: 18px 24px;
            color: var(--text-primary);
            font-size: 1rem;
            font-family: 'JetBrains Mono', monospace;
            outline: none;
            transition: all 0.2s;
        }

        #urlInput:focus {
            border-color: var(--accent);
            background: rgba(40, 40, 40, 0.9);
            box-shadow: 0 0 0 3px var(--accent-dim), var(--accent-glow);
        }

        #urlInput::placeholder {
            color: rgba(255, 255, 255, 0.2);
        }

        .btn {
            background: var(--btn-bg);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 18px 32px;
            color: var(--text-primary);
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
            backdrop-filter: blur(var(--blur));
        }

        .btn-primary {
            background: #0a0a0a;
            border-color: rgba(0, 255, 136, 0.3);
        }

        .btn-primary:hover:not(:disabled) {
            background: #1a1a1a;
            border-color: var(--accent);
            box-shadow: var(--accent-glow);
            transform: translateY(-2px);
        }

        .btn-secondary {
            background: #0a0a0a;
        }

        .btn-secondary:hover:not(:disabled) {
            background: #1a1a1a;
            border-color: rgba(255,255,255,0.2);
        }

        .btn:disabled {
            opacity: 0.4;
            cursor: not-allowed;
        }

        .btn-icon {
            font-size: 1.2rem;
        }

        /* Terminal card */
        .terminal-card {
            padding: 30px;
            margin-bottom: 30px;
            animation: fadeInUp 0.6s ease-out 0.2s both;
            display: none;
        }

        .terminal-card.active {
            display: block;
        }

        .terminal-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 20px;
            color: var(--text-secondary);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .terminal-header svg {
            width: 18px;
            height: 18px;
            stroke: var(--accent);
            fill: none;
        }

        .terminal {
            background: var(--terminal-bg);
            border-radius: 20px;
            padding: 20px;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            color: var(--terminal-text);
            font-size: 0.8rem;
            font-weight: 500;
            min-height: 300px;
            max-height: 500px;
            overflow-x: auto;  /* Allow horizontal scroll for long lines */
            overflow-y: auto;
            border: 1px solid #1a1a1a;
            box-shadow: inset 0 0 30px rgba(0,0,0,0.8), 0 0 20px rgba(0,255,136,0.1);
            line-height: 1.5;
        }

        .terminal-line {
            white-space: pre-wrap;
            word-break: break-all;
            margin-bottom: 4px;
        }

        /* Mobile adjustments */
        @media (max-width: 600px) {
            .terminal {
                font-size: 1rem;
                max-height: 400px;
                padding: 15px;
            }
            .terminal-line {
                word-break: break-word;  /* Better wrapping for long words */
            }
            .glass {
                border-radius: 20px;
            }
        }

        /* Numpad */
        .terminal-input {
            margin-top: 20px;
            display: none;
        }

        .terminal-input.active {
            display: block;
        }

        .numpad {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            justify-content: center;
        }

        .numpad-btn {
            width: 70px;
            height: 70px;
            background: #0a0a0a;
            border: 1px solid #2a2a2a;
            border-radius: 20px;
            color: var(--text-primary);
            font-size: 1.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.5);
        }

        .numpad-btn:hover:not(:disabled) {
            border-color: var(--accent);
            background: #1a1a1a;
            transform: translateY(-3px);
            box-shadow: 0 8px 20px rgba(0,255,136,0.2);
        }

        .numpad-btn:active:not(:disabled) {
            transform: translateY(0);
        }

        .numpad-btn:disabled {
            opacity: 0.4;
        }

        /* File info & audio player cards */
        .file-card, .audio-card {
            padding: 30px;
            margin-bottom: 30px;
            display: none;
            animation: fadeInUp 0.4s ease-out;
        }

        .file-card.active, .audio-card.active {
            display: block;
        }

        .card-title {
            font-size: 1.3rem;
            font-weight: 400;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            color: var(--text-secondary);
        }

        .card-title svg {
            width: 24px;
            height: 24px;
            stroke: var(--accent);
            fill: none;
        }

        .file-details {
            background: rgba(0,0,0,0.4);
            border-radius: 18px;
            padding: 24px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.95rem;
            border-left: 3px solid var(--accent);
            margin-bottom: 24px;
            box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
        }

        .file-details p {
            margin: 12px 0;
            color: var(--text-secondary);
            word-break: break-all;
        }

        .file-details strong {
            color: var(--accent);
            font-weight: 600;
            min-width: 100px;
            display: inline-block;
            margin-right: 12px;
        }

        /* Custom Audio Player */
        .custom-player {
            background: rgba(0, 0, 0, 0.4);
            border-radius: 40px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid var(--card-border);
            box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
        }

        .player-controls {
            display: flex;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
        }

        .play-pause-btn {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: var(--btn-bg);
            border: 2px solid var(--accent);
            color: var(--accent);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s;
            box-shadow: 0 0 15px var(--accent-dim);
        }

        .play-pause-btn svg {
            width: 30px;
            height: 30px;
            stroke: currentColor;
            fill: none;
        }

        .play-pause-btn:hover {
            background: var(--accent);
            color: #000;
            transform: scale(1.05);
        }

        .time-display {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1rem;
            color: var(--accent);
            min-width: 120px;
        }

        .progress-container {
            flex: 1;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .progress-bar {
            flex: 1;
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            cursor: pointer;
            position: relative;
        }

        .progress-fill {
            height: 100%;
            background: var(--accent);
            border-radius: 4px;
            width: 0%;
            transition: width 0.1s linear;
        }

        .volume-control {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .volume-btn {
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 1.5rem;
            cursor: pointer;
            transition: color 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .volume-btn:hover {
            color: var(--accent);
        }

        .volume-slider {
            width: 80px;
            height: 4px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 2px;
            cursor: pointer;
            position: relative;
        }

        .volume-fill {
            height: 100%;
            background: var(--accent);
            border-radius: 2px;
            width: 100%;
        }

        input[type=range] {
            display: none;
        }

        /* Custom Download Button */
        .download-btn-container {
            display: flex;
            justify-content: center;
            margin-top: 20px;
        }

        .download-label {
            background-color: transparent;
            border: 2px solid var(--accent);
            display: inline-flex;
            align-items: center;
            border-radius: 50px;
            cursor: pointer;
            transition: all 0.3s ease;
            padding: 5px;
            text-decoration: none;
            color: var(--text-primary);
        }

        .download-label:hover {
            border-color: #88ff88;
            box-shadow: var(--accent-glow);
        }

        .download-circle {
            height: 45px;
            width: 45px;
            border-radius: 50%;
            background-color: var(--accent);
            display: flex;
            justify-content: center;
            align-items: center;
            transition: all 0.3s ease;
            box-shadow: 0 0 10px var(--accent-dim);
        }

        .download-circle svg {
            color: #000;
            width: 30px;
            stroke: currentColor;
            stroke-width: 2;
        }

        .download-text {
            font-size: 17px;
            font-weight: 600;
            color: var(--text-primary);
            margin-left: 12px;
            margin-right: 18px;
            transition: color 0.3s ease;
        }

        .download-label:hover .download-text {
            color: var(--accent);
        }

        /* Status messages */
        #status {
            margin-top: 20px;
        }

        .status {
            padding: 16px 24px;
            border-radius: 14px;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 12px;
            background: rgba(0,0,0,0.5);
            backdrop-filter: blur(10px);
            border-left: 4px solid;
            animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .status.info {
            border-color: #3399ff;
            color: #aaccff;
        }
        .status.success {
            border-color: #00ff88;
            color: #aaffcc;
        }
        .status.error {
            border-color: #ff5555;
            color: #ffaaaa;
        }

        /* ANSI colors for terminal */
        .ansi-red { color: #ff5555; }
        .ansi-green { color: #aaffaa; }
        .ansi-yellow { color: #ffff88; }
        .ansi-blue { color: #8888ff; }
        .ansi-magenta { color: #ff88ff; }
        .ansi-cyan { color: #88ffff; }
        .ansi-white { color: #ffffff; }
        .ansi-bold { font-weight: bold; }
        .ansi-blink { animation: blink 1s infinite; }

        @keyframes blink {
            0%,50% { opacity: 1; }
            51%,100% { opacity: 0.3; }
        }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #0a0a0a; }
        ::-webkit-scrollbar-thumb { background: #2a2a2a; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #3a3a3a; }

        /* Animations */
        @keyframes fadeInDown {
            from { opacity: 0; transform: translateY(-30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">YTMP3-DL</div>
            <div class="tagline">OLED · TERMINAL · LOCAL</div>
        </div>

        <!-- Input Card -->
        <div class="glass input-card">
            <label class="input-label">🔗 YouTube URL</label>
            <div class="input-wrapper">
                <input type="text" id="urlInput" placeholder="https://youtube.com/watch?v=..." />
                <button class="btn btn-primary" id="convertBtn" onclick="startConversion()">
                    <span class="btn-icon">⚡</span> Convert
                </button>
                <button class="btn btn-secondary" id="clearBtn" onclick="clearTerminal()">
                    <span class="btn-icon">🗑️</span> Clear
                </button>
            </div>
            <div id="status"></div>
        </div>

        <!-- Terminal Card (hidden by default) -->
        <div class="glass terminal-card" id="terminalCard">
            <div class="terminal-header">
                <svg viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path d="M4 17l6-6-6-6M12 19h8" />
                </svg>
                <span>TERMINAL OUTPUT</span>
            </div>
            <div class="terminal" id="terminal"></div>
            <div class="terminal-input" id="terminalInput">
                <div class="numpad">
                    <button class="numpad-btn" onclick="sendNumpad('1')">1</button>
                    <button class="numpad-btn" onclick="sendNumpad('2')">2</button>
                    <button class="numpad-btn" onclick="sendNumpad('3')">3</button>
                    <button class="numpad-btn" onclick="sendNumpad('4')">4</button>
                    <button class="numpad-btn" onclick="sendNumpad('5')">5</button>
                    <button class="numpad-btn" onclick="sendNumpad('6')">6</button>
                    <button class="numpad-btn" onclick="sendNumpad('7')">7</button>
                    <button class="numpad-btn" onclick="sendNumpad('8')">8</button>
                </div>
            </div>
        </div>

        <!-- File Info Card -->
        <div class="glass file-card" id="fileInfo">
            <div class="card-title">
                <svg viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" />
                    <path d="M14 2v6h6" />
                </svg>
                FILE INFORMATION
            </div>
            <div class="file-details" id="fileDetails"></div>
        </div>

        <!-- Audio Player Card with Custom Player -->
        <div class="glass audio-card" id="audioPlayer">
            <div class="card-title">
                <svg viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path d="M9 18V5l12-2v13" />
                    <circle cx="6" cy="18" r="3" />
                    <circle cx="18" cy="16" r="3" />
                </svg>
                AUDIO READY
            </div>
            <!-- Hidden native audio element -->
            <audio id="audioElement" style="display: none;" preload="metadata"></audio>
            <!-- Custom Player Controls -->
            <div class="custom-player">
                <div class="player-controls">
                    <div class="play-pause-btn" id="playPauseBtn">
                        <!-- Play icon (triangle) -->
                        <svg class="play-icon" viewBox="0 0 24 24" width="30" height="30" stroke="currentColor" stroke-width="1.5" fill="none">
                            <polygon points="5 3 19 12 5 21 5 3" />
                        </svg>
                        <!-- Pause icon (two bars) initially hidden -->
                        <svg class="pause-icon" viewBox="0 0 24 24" width="30" height="30" stroke="currentColor" stroke-width="1.5" fill="none" style="display: none;">
                            <line x1="6" y1="4" x2="6" y2="20" />
                            <line x1="18" y1="4" x2="18" y2="20" />
                        </svg>
                    </div>
                    <div class="time-display" id="timeDisplay">00:00 / 00:00</div>
                    <div class="progress-container">
                        <div class="progress-bar" id="progressBar">
                            <div class="progress-fill" id="progressFill"></div>
                        </div>
                    </div>
                    <div class="volume-control">
                        <button class="volume-btn" id="muteBtn">🔊</button>
                        <div class="volume-slider" id="volumeSlider">
                            <div class="volume-fill" id="volumeFill" style="width: 100%;"></div>
                        </div>
                    </div>
                </div>
            </div>
            <!-- Custom Download Button -->
            <div class="download-btn-container">
                <a href="#" class="download-label" id="downloadBtn" download onclick="handleDownload(event)">
                    <span class="download-circle">
                        <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 19V5m0 14-4-4m4 4 4-4" />
                        </svg>
                    </span>
                    <span class="download-text">Download</span>
                </a>
            </div>
        </div>
    </div>

        <script>
        const socket = io();
        let sessionId = null;
        let inputLocked = false;
        let currentFilename = null;

        // Audio player elements
        const audio = document.getElementById('audioElement');
        const playPauseBtn = document.getElementById('playPauseBtn');
        const playIcon = document.querySelector('.play-icon');
        const pauseIcon = document.querySelector('.pause-icon');
        const timeDisplay = document.getElementById('timeDisplay');
        const progressBar = document.getElementById('progressBar');
        const progressFill = document.getElementById('progressFill');
        const muteBtn = document.getElementById('muteBtn');
        const volumeSlider = document.getElementById('volumeSlider');
        const volumeFill = document.getElementById('volumeFill');

        // Audio player state
        let isPlaying = false;
        let isMuted = false;
        let volume = 1.0;

        // Update play/pause icons based on playback state
        audio.addEventListener('play', () => {
            isPlaying = true;
            playIcon.style.display = 'none';
            pauseIcon.style.display = 'block';
        });
        audio.addEventListener('pause', () => {
            isPlaying = false;
            playIcon.style.display = 'block';
            pauseIcon.style.display = 'none';
        });
        audio.addEventListener('ended', () => {
            isPlaying = false;
            playIcon.style.display = 'block';
            pauseIcon.style.display = 'none';
            progressFill.style.width = '0%';
            timeDisplay.textContent = formatTime(0) + ' / ' + formatTime(audio.duration);
        });

        // Update time display and progress bar
        audio.addEventListener('timeupdate', () => {
            const current = audio.currentTime;
            const duration = audio.duration || 0;
            if (duration) {
                const percent = (current / duration) * 100;
                progressFill.style.width = percent + '%';
                timeDisplay.textContent = formatTime(current) + ' / ' + formatTime(duration);
            }
        });

        // When metadata is loaded, update duration display immediately
        audio.addEventListener('loadedmetadata', () => {
            const duration = audio.duration || 0;
            timeDisplay.textContent = '00:00 / ' + formatTime(duration);
        });

        // Seek when clicking on progress bar
        progressBar.addEventListener('click', (e) => {
            const rect = progressBar.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const width = rect.width;
            const percent = clickX / width;
            if (audio.duration) {
                audio.currentTime = percent * audio.duration;
            }
        });

        // Volume control
        volumeSlider.addEventListener('click', (e) => {
            const rect = volumeSlider.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const width = rect.width;
            const percent = Math.min(1, Math.max(0, clickX / width));
            volume = percent;
            audio.volume = volume;
            volumeFill.style.width = (volume * 100) + '%';
            updateMuteIcon();
        });

        muteBtn.addEventListener('click', () => {
            if (isMuted) {
                audio.muted = false;
                isMuted = false;
                audio.volume = volume;
                volumeFill.style.width = (volume * 100) + '%';
                muteBtn.textContent = '🔊';
            } else {
                audio.muted = true;
                isMuted = true;
                volumeFill.style.width = '0%';
                muteBtn.textContent = '🔇';
            }
        });

        function updateMuteIcon() {
            if (volume === 0) {
                muteBtn.textContent = '🔇';
                isMuted = true;
                audio.muted = true;
            } else {
                muteBtn.textContent = '🔊';
                isMuted = false;
                audio.muted = false;
            }
        }

        function formatTime(seconds) {
            if (isNaN(seconds)) return '00:00';
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return mins.toString().padStart(2, '0') + ':' + secs.toString().padStart(2, '0');
        }

        // Toggle play/pause
        playPauseBtn.addEventListener('click', () => {
            if (audio.src) {
                if (audio.paused) {
                    audio.play();
                } else {
                    audio.pause();
                }
            }
        });

        socket.on('connect', () => console.log('Connected'));

        socket.on('terminal_output', (data) => {
            // Skip lines containing warnings
            if (data.output.includes('warnings.warn') || 
                data.output.includes('RequestsDependencyWarning') || 
                data.output.includes('urllib3') || 
                data.output.includes('chardet')) {
                return;
            }

            const terminal = document.getElementById('terminal');
            const line = document.createElement('div');
            line.className = 'terminal-line';
            line.innerHTML = parseANSI(data.output);
            terminal.appendChild(line);
            terminal.scrollTop = terminal.scrollHeight;

            const text = data.output.toLowerCase();
            if (!inputLocked && (text.includes('select') || text.includes('[1-9]') || text.includes('»') || text.includes('quality'))) {
                setTimeout(() => {
                    document.getElementById('terminalInput').classList.add('active');
                }, 300);
            }
        });

        socket.on('request_input', () => {
            if (!inputLocked) {
                setTimeout(() => {
                    document.getElementById('terminalInput').classList.add('active');
                }, 500);
            }
        });

        socket.on('download_ready', (data) => {
            showStatus('Download complete!', 'success');
            document.getElementById('terminalInput').classList.remove('active');
            document.getElementById('terminalCard').classList.remove('active'); // Hide terminal
            inputLocked = false;
            currentFilename = data.filename;

            const audioPlayer = document.getElementById('audioPlayer');
            const downloadBtn = document.getElementById('downloadBtn');

            // Set audio source to streaming endpoint (supports range requests)
            audio.src = `/api/stream-file/${data.filename}`;
            // Set download button to download endpoint (forces attachment)
            downloadBtn.href = `/api/download-file/${data.filename}`;
            downloadBtn.download = data.filename;
            audioPlayer.classList.add('active');

            const fileInfo = document.getElementById('fileInfo');
            const fileDetails = document.getElementById('fileDetails');
            fileDetails.innerHTML = `
                <p><strong>File Name:</strong> ${data.filename}</p>
                <p><strong>Size:</strong> ${data.size}</p>
            `;
            fileInfo.classList.add('active');

            document.getElementById('convertBtn').disabled = false;

            // Scroll to bottom after download is ready
            setTimeout(() => {
                document.documentElement.scrollTop = document.documentElement.scrollHeight;
                document.body.scrollTop = document.body.scrollHeight;
            }, 300);
        });

        socket.on('file_deleted', (data) => {
            showStatus('File deleted. Ready for new conversion!', 'success');
            document.getElementById('fileInfo').classList.remove('active');
            document.getElementById('audioPlayer').classList.remove('active');
            audio.pause();
            audio.src = '';
            currentFilename = null;
            document.getElementById('urlInput').value = '';
            document.getElementById('convertBtn').disabled = false;
            // Reset player UI
            playIcon.style.display = 'block';
            pauseIcon.style.display = 'none';
            progressFill.style.width = '0%';
            timeDisplay.textContent = '00:00 / 00:00';
        });

        socket.on('error', (data) => {
            showStatus('Error: ' + data.message, 'error');
            document.getElementById('convertBtn').disabled = false;
            document.getElementById('terminalInput').classList.remove('active');
            document.getElementById('terminalCard').classList.remove('active'); // Hide terminal on error too
            inputLocked = false;
        });

        // Delete file on page unload (refresh/close) if not already downloaded
        window.addEventListener('beforeunload', function() {
            if (currentFilename) {
                navigator.sendBeacon(`/api/delete-file/${currentFilename}`);
            }
        });

        function startConversion() {
            const url = document.getElementById('urlInput').value.trim();
            if (!url) {
                showStatus('Please enter a YouTube URL', 'error');
                return;
            }
            if (!url.includes('youtube.com') && !url.includes('youtu.be')) {
                showStatus('Enter a valid YouTube URL', 'error');
                return;
            }

            document.getElementById('convertBtn').disabled = true;
            document.getElementById('audioPlayer').classList.remove('active');
            document.getElementById('fileInfo').classList.remove('active');
            document.getElementById('terminal').innerHTML = '';
            document.getElementById('terminalCard').classList.add('active'); // Show terminal
            
            // Auto-scroll to the very bottom of the webpage after terminal renders
            setTimeout(() => {
                document.documentElement.scrollTop = document.documentElement.scrollHeight;
                document.body.scrollTop = document.body.scrollHeight;
                window.scrollTo(0, document.body.scrollHeight);
            }, 1000);
            
            inputLocked = false;
            showStatus('Starting conversion...', 'info');

            sessionId = Date.now().toString();
            socket.emit('start_conversion', { url: url, session_id: sessionId });
        }

        function clearTerminal() {
            document.getElementById('terminal').innerHTML = '';
        }

        function sendNumpad(value) {
            if (inputLocked) return;
            inputLocked = true;

            const buttons = document.querySelectorAll('.numpad-btn');
            buttons.forEach(btn => btn.disabled = true);

            const terminal = document.getElementById('terminal');
            const line = document.createElement('div');
            line.className = 'terminal-line';
            line.innerHTML = `<span class="ansi-cyan ansi-bold">» ${value}</span>`;
            terminal.appendChild(line);
            terminal.scrollTop = terminal.scrollHeight;

            document.getElementById('terminalInput').classList.remove('active');

            socket.emit('terminal_input', { session_id: sessionId, input: value });

            setTimeout(() => {
                buttons.forEach(btn => btn.disabled = false);
            }, 3000);
        }

        function handleDownload(event) {
            event.preventDefault();
            const downloadBtn = document.getElementById('downloadBtn');
            const href = downloadBtn.href;
            
            // Trigger download
            const link = document.createElement('a');
            link.href = href;
            link.download = currentFilename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Auto-delete file after download and reset UI
            setTimeout(() => {
                if (currentFilename) {
                    socket.emit('delete_file', { filename: currentFilename });
                }
            }, 500);
        }

        function showStatus(message, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.innerHTML = `<div class="status ${type}">${message}</div>`;
        }

        function parseANSI(text) {
            text = text.replace(/\033\[\d*[HJKABCDEFGST]/g, '');
            text = text.replace(/\033\[2J/g, '');
            text = text.replace(/\033\[\?25[hl]/g, '');
            text = text.replace(/\033\[\d+;\d+H/g, '');
            text = text.replace(/\033\[91m/g, '<span class="ansi-red">');
            text = text.replace(/\033\[92m/g, '<span class="ansi-green">');
            text = text.replace(/\033\[93m/g, '<span class="ansi-yellow">');
            text = text.replace(/\033\[94m/g, '<span class="ansi-blue">');
            text = text.replace(/\033\[95m/g, '<span class="ansi-magenta">');
            text = text.replace(/\033\[96m/g, '<span class="ansi-cyan">');
            text = text.replace(/\033\[97m/g, '<span class="ansi-white">');
            text = text.replace(/\033\[1m/g, '<span class="ansi-bold">');
            text = text.replace(/\033\[5m/g, '<span class="ansi-blink">');
            text = text.replace(/\033\[0m/g, '</span>');
            text = text.replace(/\033\[\d+m/g, '</span>');
            return text;
        }

        document.getElementById('urlInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') startConversion();
        });

        document.addEventListener('keydown', (e) => {
            if (inputLocked) return;
            if (document.getElementById('terminalInput').classList.contains('active')) {
                if (e.key >= '1' && e.key <= '8') {
                    sendNumpad(e.key);
                    e.preventDefault();
                }
            }
        });
    </script>
</body>
</html>
"""

# ----------------------------------------------------------------------
# Backend – No SFTP, direct file serving with range support
# ----------------------------------------------------------------------

@app.route('/')
def index():
    return HTML_TEMPLATE

@socketio.on('start_conversion')
def handle_conversion(data):
    url = data['url']
    session_id = data['session_id']
    client_id = request.sid
    
    print(f"[+] Starting conversion for: {url} (Client: {client_id})")
    
    thread = threading.Thread(target=run_conversion, args=(url, session_id, client_id))
    thread.daemon = True
    thread.start()

@socketio.on('terminal_input')
def handle_terminal_input(data):
    session_id = data['session_id']
    user_input = data['input']
    client_id = request.sid
    
    if session_id in active_processes:
        process_info = active_processes[session_id]
        if process_info['client_id'] != client_id:
            print(f"[!] Blocked input from unauthorized client: {client_id}")
            return
        
        process = process_info['process']
        try:
            process.stdin.write(user_input + '\n')
            process.stdin.flush()
            print(f"[+] Sent input: {user_input} (Client: {client_id})")
        except Exception as e:
            print(f"[!] Error sending input: {e}")

def run_conversion(url, session_id, client_id):
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'mp3.py')
        
        if not os.path.exists(script_path):
            socketio.emit('error', {'message': 'mp3.py not found!'}, room=client_id)
            return
        
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        
        process = subprocess.Popen(
            ['python3', '-u', script_path, url],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=0,
            universal_newlines=True,
            env=env
        )
        
        active_processes[session_id] = {
            'process': process,
            'url': url,
            'client_id': client_id
        }
        
        output_buffer = ""
        while True:
            char = process.stdout.read(1)
            if not char:
                break
            
            output_buffer += char
            
            if char == '\n':
                # Skip lines containing warnings
                if any(x in output_buffer for x in ['warnings.warn', 'RequestsDependencyWarning', 'urllib3', 'chardet']):
                    output_buffer = ""
                    continue
                    
                socketio.emit('terminal_output', {'output': output_buffer.rstrip()}, room=client_id)
                
                lower_buffer = output_buffer.lower()
                if ('select' in lower_buffer and '[1-9]' in lower_buffer) or \
                   ('»' in output_buffer) or \
                   ('enter' in lower_buffer and 'quality' in lower_buffer):
                    socketio.emit('request_input', {}, room=client_id)
                
                output_buffer = ""
        
        process.wait()
        
        print("[+] Conversion complete, locating file...")
        socketio.emit('terminal_output', {'output': '\n[+] Locating file...'}, room=client_id)
        
        time.sleep(1)  # Give the file system a moment
        file_info = get_latest_file()
        
        if file_info:
            socketio.emit('download_ready', {
                'filename': file_info['name'],
                'size': format_size(file_info['size'])
            }, room=client_id)
        else:
            socketio.emit('error', {'message': 'No output file found'}, room=client_id)
        
        if session_id in active_processes:
            del active_processes[session_id]
            
    except Exception as e:
        print(f"[!] Error: {e}")
        traceback.print_exc()
        socketio.emit('error', {'message': str(e)}, room=client_id)

def get_latest_file():
    """Get the most recent audio file from OUTPUT_DIR"""
    try:
        if not os.path.exists(OUTPUT_DIR):
            print(f"[!] Output directory does not exist: {OUTPUT_DIR}")
            return None
        
        files = []
        for f in os.listdir(OUTPUT_DIR):
            full_path = os.path.join(OUTPUT_DIR, f)
            if os.path.isfile(full_path) and f.endswith(('.mp3', '.flac', '.wav', '.m4a', '.opus')):
                files.append({
                    'name': f,
                    'mtime': os.path.getmtime(full_path),
                    'size': os.path.getsize(full_path)
                })
        
        if not files:
            return None
        
        latest = max(files, key=lambda x: x['mtime'])
        return latest
        
    except Exception as e:
        print(f"[!] Error scanning output directory: {e}")
        return None

def format_size(bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"

@socketio.on('delete_file')
def handle_delete_file(data):
    filename = data['filename']
    client_id = request.sid
    
    # Prevent path traversal
    if '..' in filename or filename.startswith('/'):
        socketio.emit('error', {'message': 'Invalid filename'}, room=client_id)
        return
    
    try:
        file_path = os.path.join(OUTPUT_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[+] Deleted file: {filename}")
            socketio.emit('file_deleted', 
                         {'message': f'Successfully deleted {filename}'},
                         room=client_id)
        else:
            print(f"[!] File not found: {filename}")
            socketio.emit('error', 
                         {'message': f'File not found: {filename}'}, 
                         room=client_id)
        
    except Exception as e:
        print(f"[!] Delete error: {e}")
        socketio.emit('error', {'message': f'Failed to delete file: {str(e)}'}, room=client_id)

@app.route('/api/stream-file/<filename>')
def stream_file(filename):
    """Serve audio file for streaming with range support"""
    # Prevent path traversal
    if '..' in filename or filename.startswith('/'):
        abort(400, description="Invalid filename")
    
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        abort(404, description="File not found")
    
    # Determine MIME type
    mime_type = 'audio/mpeg'
    if filename.endswith('.m4a'):
        mime_type = 'audio/mp4'
    elif filename.endswith('.flac'):
        mime_type = 'audio/flac'
    elif filename.endswith('.wav'):
        mime_type = 'audio/wav'
    elif filename.endswith('.opus'):
        mime_type = 'audio/opus'
    
    # Enable range handling and set proper headers
    response = send_file(file_path, mimetype=mime_type, conditional=True)
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/download-file/<filename>')
def download_file(filename):
    """Serve audio file as download (attachment)"""
    # Prevent path traversal
    if '..' in filename or filename.startswith('/'):
        abort(400, description="Invalid filename")
    
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        abort(404, description="File not found")
    
    # Determine MIME type
    mime_type = 'audio/mpeg'
    if filename.endswith('.m4a'):
        mime_type = 'audio/mp4'
    elif filename.endswith('.flac'):
        mime_type = 'audio/flac'
    elif filename.endswith('.wav'):
        mime_type = 'audio/wav'
    elif filename.endswith('.opus'):
        mime_type = 'audio/opus'
    
    return send_file(file_path, mimetype=mime_type, as_attachment=True, download_name=filename)

@app.route('/api/delete-file/<filename>', methods=['POST'])
def delete_file_http(filename):
    """HTTP endpoint for deleting files (used by sendBeacon on page unload)"""
    # Prevent path traversal
    if '..' in filename or filename.startswith('/'):
        abort(400, description="Invalid filename")
    
    try:
        file_path = os.path.join(OUTPUT_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[+] Deleted file via HTTP: {filename}")
            return {'status': 'success', 'message': f'Deleted {filename}'}, 200
        else:
            print(f"[!] File not found: {filename}")
            return {'status': 'error', 'message': f'File not found: {filename}'}, 404
    except Exception as e:
        print(f"[!] Delete error: {e}")
        return {'status': 'error', 'message': f'Failed to delete: {str(e)}'}, 500


# ----------------------------------------------------------------------
# Cloudflare Tunnel integration
# ----------------------------------------------------------------------
def start_cloudflare_tunnel():
    """Launch cloudflared tunnel, show logs until URL, then go completely silent (but keep running)."""
    MAX_HYPHENS = 3  # e.g., "eagle-athletes-merger-wagner" has 3 hyphens

    try:
        process = subprocess.Popen(
            ['cloudflared', 'tunnel', '--url', 'http://localhost:1234'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
    except FileNotFoundError:
        print("\n[!] cloudflared not found. Install from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
        print("    The app will still run locally on http://localhost:1234\n")
        return None

    tunnel_url = None
    url_found = threading.Event()

    def read_output():
        nonlocal tunnel_url
        for line in iter(process.stdout.readline, ''):
            if not tunnel_url:
                match = re.search(r'https://[a-zA-Z0-9.-]+\.trycloudflare\.com', line)
                if match:
                    tunnel_url = match.group(0)
                    url_found.set()

                    # Check if the subdomain is too long (many hyphens)
                    subdomain = tunnel_url.split('//')[1].split('.trycloudflare.com')[0]
                    hyphen_count = subdomain.count('-')
                    if hyphen_count > MAX_HYPHENS:
                        print("\nℹ️  The tunnel subdomain is long ({} hyphens).".format(hyphen_count))
                        print("   If you'd prefer a shorter one, it may take up to a minute –")
                        print("   you can restart the app to try again.\n")

                    # Print the banner once
                    print("\n" + "="*60)
                    print("\n🌐  CLOUDFLARE TUNNEL ACTIVE: {}".format(tunnel_url))
                    print("\n" + "="*60 + "\n")
                    # From now on, silently consume all future output
                    continue
            # After URL found, we still read but discard silently.
        # If the loop ends (process died), check if we ever got the URL
        if not url_found.is_set():
            print("\n[!] Cloudflare tunnel process ended without providing a URL.")
            print("    Check your network or run without hiding logs to debug.\n")
        elif url_found.is_set():
            print("\n[!] Cloudflare tunnel stopped unexpectedly.")
            print("    The public URL may no longer be accessible.\n")

    thread = threading.Thread(target=read_output, daemon=True)
    thread.start()
    return process

if __name__ == '__main__':
    print("""
╔═════════════════════════════════════════════════════════════════════╗
║                                                                     ║
║   YTMP3-DL WEB TERMINAL · OLED EDITION (FINAL)                      ║
║   Running on: http://localhost:1234                                 ║
║   Output directory: ~/ytmp3-mp4/music-output                        ║
║   Terminal font: 0.8rem · Auto‑hide after completion                ║
║   Filtered warnings · Auto‑scroll to terminal (fixed)               ║
║   Auto-delete files after download · Custom audio player            ║
║   Secure dual‑endpoint (stream + download) with range support       ║
║   Stylish download button (no "Open") · Backend warnings suppressed ║
║   Now with Cloudflare Tunnel & improved play/pause button           ║
║                                                                     ║
╚═════════════════════════════════════════════════════════════════════╝
    """)
    
    # Ensure output directory exists (optional)
    if not os.path.exists(OUTPUT_DIR):
        print(f"[!] Warning: Output directory {OUTPUT_DIR} does not exist. Please create it.")
    
    # Start Cloudflare tunnel (if enabled and cloudflared is installed)
    enable_tunnel = os.getenv('ENABLE_CLOUDFLARE_TUNNEL', 'false').lower() in {'1', 'true', 'yes'}
    tunnel_process = start_cloudflare_tunnel() if enable_tunnel else None

    # Ensure tunnel is killed when the script exits
    def cleanup():
        if tunnel_process and tunnel_process.poll() is None:
            print("\n[+] Terminating Cloudflare tunnel...")
            tunnel_process.terminate()
            try:
                tunnel_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                tunnel_process.kill()
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))

    try:
        socketio.run(app, host='0.0.0.0', port=1234, debug=False)
    except KeyboardInterrupt:
        pass  # cleanup will run via at exit
