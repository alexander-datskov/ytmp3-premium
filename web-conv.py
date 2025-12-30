#!/usr/bin/env python3
"""
YTMP3-DL Web Terminal Server
Runs on port 1234 with embedded HTML, live terminal, and SFTP download
"""

from flask import Flask, render_template_string, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import subprocess
import threading
import os
import time
import paramiko
from io import BytesIO
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ytmp3-dl-secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# SFTP Configuration
SFTP_HOST = 'rasp-alex2.local'
SFTP_PORT = 22
SFTP_USER = 'rasp-alex2'
SFTP_PASS = '120313'
SFTP_DIR = '/home/rasp-alex2/Downloads'

# Active processes
active_processes = {}

# HTML Template (embedded)
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YTMP3-DL Web Terminal</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.5.4/socket.io.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 25%, #7e8ba3 50%, #b8c6db 75%, #f5f7fa 100%);
            background-attachment: fixed;
            min-height: 100vh;
            padding: 40px 20px;
            position: relative;
            overflow-x: hidden;
        }

        /* Winter Snowflakes */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: 
                radial-gradient(2px 2px at 20% 30%, white, transparent),
                radial-gradient(2px 2px at 60% 70%, white, transparent),
                radial-gradient(1px 1px at 50% 50%, white, transparent),
                radial-gradient(1px 1px at 80% 10%, white, transparent),
                radial-gradient(2px 2px at 90% 60%, white, transparent),
                radial-gradient(1px 1px at 33% 80%, white, transparent);
            background-size: 200% 200%;
            animation: snowfall 20s linear infinite;
            opacity: 0.6;
            pointer-events: none;
            z-index: 1;
        }

        @keyframes snowfall {
            0% { transform: translateY(0); }
            100% { transform: translateY(100%); }
        }

        /* Frosted Glass Effect */
        .glass {
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: 
                0 8px 32px 0 rgba(31, 38, 135, 0.15),
                inset 0 1px 0 0 rgba(255, 255, 255, 0.5);
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
            z-index: 10;
        }

        /* Header Section */
        .header {
            text-align: center;
            padding: 60px 0 40px;
            position: relative;
        }

        .logo-container {
            display: inline-flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 20px;
        }

        .logo-icon {
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.5rem;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
            animation: float 3s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }

        .title {
            font-size: 4rem;
            font-weight: 800;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #667eea 100%);
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: gradientShift 3s ease infinite;
            letter-spacing: -2px;
            margin-bottom: 10px;
        }

        @keyframes gradientShift {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }

        .subtitle {
            font-size: 1.1rem;
            color: #4a5568;
            font-weight: 500;
            letter-spacing: 1px;
        }

        /* Card Styles */
        .card {
            border-radius: 24px;
            padding: 40px;
            margin-bottom: 30px;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .card:hover {
            transform: translateY(-4px);
            box-shadow: 
                0 20px 60px 0 rgba(31, 38, 135, 0.2),
                inset 0 1px 0 0 rgba(255, 255, 255, 0.6);
        }

        /* Input Section */
        .input-section {
            position: relative;
        }

        .input-label {
            display: block;
            font-size: 0.875rem;
            font-weight: 600;
            color: #4a5568;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .input-wrapper {
            position: relative;
            margin-bottom: 24px;
        }

        .input-icon {
            position: absolute;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1.3rem;
            color: #a0aec0;
            z-index: 1;
        }

        .url-input {
            width: 100%;
            background: rgba(255, 255, 255, 0.9);
            border: 2px solid rgba(102, 126, 234, 0.2);
            border-radius: 16px;
            padding: 20px 20px 20px 60px;
            color: #2d3748;
            font-family: 'JetBrains Mono', monospace;
            font-size: 1rem;
            font-weight: 500;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }

        .url-input:focus {
            outline: none;
            border-color: #667eea;
            background: white;
            box-shadow: 
                0 4px 20px rgba(102, 126, 234, 0.15),
                0 0 0 4px rgba(102, 126, 234, 0.1);
            transform: translateY(-2px);
        }

        .url-input::placeholder {
            color: #a0aec0;
            font-weight: 400;
        }

        /* Button Styles */
        .btn-container {
            display: flex;
            gap: 16px;
        }

        .btn {
            flex: 1;
            padding: 18px 32px;
            font-family: 'Inter', sans-serif;
            font-size: 1rem;
            font-weight: 600;
            text-transform: none;
            letter-spacing: 0.5px;
            border: none;
            border-radius: 14px;
            cursor: pointer;
            position: relative;
            overflow: hidden;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
            transition: left 0.5s;
        }

        .btn:hover::before {
            left: 100%;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);
        }

        .btn-primary:hover:not(:disabled) {
            box-shadow: 0 15px 35px rgba(102, 126, 234, 0.4);
            transform: translateY(-2px);
        }

        .btn-primary:active:not(:disabled) {
            transform: translateY(0);
        }

        .btn-secondary {
            background: white;
            color: #667eea;
            border: 2px solid #667eea;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.15);
        }

        .btn-secondary:hover:not(:disabled) {
            background: #667eea;
            color: white;
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
            transform: translateY(-2px);
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .btn-icon {
            font-size: 1.2rem;
        }

        /* Status Messages */
        #status {
            margin-top: 20px;
        }

        .status {
            padding: 16px 24px;
            border-radius: 12px;
            text-align: left;
            font-weight: 500;
            font-size: 0.95rem;
            display: flex;
            align-items: center;
            gap: 12px;
            animation: slideDown 0.3s ease;
        }

        @keyframes slideDown {
            from {
                opacity: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .status::before {
            content: '';
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
        }

        .status.info {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            color: #1565c0;
            border-left: 4px solid #1976d2;
        }

        .status.info::before {
            background: #1976d2;
        }

        .status.success {
            background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
            color: #2e7d32;
            border-left: 4px solid #388e3c;
        }

        .status.success::before {
            background: #388e3c;
        }

        .status.error {
            background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
            color: #c62828;
            border-left: 4px solid #d32f2f;
        }

        .status.error::before {
            background: #d32f2f;
        }

        /* Terminal Section - KEPT AS IS */
        .terminal-card {
            border-radius: 24px;
            padding: 40px;
            margin-bottom: 30px;
        }

        .terminal-header-text {
            font-size: 1.5rem;
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .terminal-header-text::before {
            content: '⚡';
            font-size: 1.8rem;
        }

        .terminal {
            background: #1e1e1e;
            border-radius: 16px;
            padding: 20px;
            font-family: 'Courier New', monospace;
            color: #00ff00;
            font-size: 1.1rem;
            min-height: 546px;
            max-height: 728px;
            overflow-y: auto;
            margin-bottom: 20px;
            display: none;
            width: 130%;
            margin-left: -15%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }

        .terminal.active {
            display: block;
        }

        .terminal-line {
            margin-bottom: 5px;
            white-space: pre-wrap;
            word-break: break-all;
        }

        .terminal-input {
            display: none;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
        }

        .terminal-input.active {
            display: flex;
        }

        .numpad {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            max-width: 600px;
        }

        .numpad-btn {
            padding: 20px;
            background: linear-gradient(135deg, #00ff00 0%, #00dd00 100%);
            color: #1e1e1e;
            border: none;
            border-radius: 12px;
            font-weight: bold;
            font-size: 1.3rem;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            font-family: 'JetBrains Mono', monospace;
            box-shadow: 0 4px 15px rgba(0, 255, 0, 0.2);
        }

        .numpad-btn:hover:not(:disabled) {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0, 255, 0, 0.4);
            background: linear-gradient(135deg, #00ff41 0%, #00ee00 100%);
        }

        .numpad-btn:active:not(:disabled) {
            transform: translateY(0);
        }

        .numpad-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        /* ANSI Color Classes */
        .ansi-red { color: #ff0051; }
        .ansi-green { color: #00ff41; }
        .ansi-yellow { color: #ffff00; }
        .ansi-blue { color: #0099ff; }
        .ansi-magenta { color: #ff00ff; }
        .ansi-cyan { color: #00ffff; }
        .ansi-white { color: #ffffff; }
        .ansi-bold { font-weight: bold; }

        /* File Info Section */
        .file-info {
            border-radius: 24px;
            padding: 40px;
            margin-bottom: 30px;
            display: none;
        }

        .file-info.active {
            display: block;
            animation: slideDown 0.4s ease;
        }

        .file-info h3 {
            color: #2d3748;
            margin-bottom: 24px;
            font-size: 1.5rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .file-details {
            font-family: 'JetBrains Mono', monospace;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
            padding: 24px;
            border-radius: 16px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        }

        .file-details p {
            margin: 12px 0;
            color: #4a5568;
            font-size: 0.95rem;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .file-details strong {
            color: #2d3748;
            font-weight: 600;
            min-width: 140px;
        }

        .file-actions-row {
            display: flex;
            gap: 12px;
        }

        .delete-btn {
            padding: 14px 28px;
            background: linear-gradient(135deg, #f56565 0%, #c53030 100%);
            color: white;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            font-weight: 600;
            font-size: 0.95rem;
            display: flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0 6px 20px rgba(245, 101, 101, 0.3);
        }

        .delete-btn:hover {
            background: linear-gradient(135deg, #fc8181 0%, #e53e3e 100%);
            box-shadow: 0 10px 30px rgba(245, 101, 101, 0.4);
            transform: translateY(-2px);
        }

        /* Audio Player */
        .audio-player {
            border-radius: 24px;
            padding: 40px;
            margin-bottom: 30px;
            display: none;
        }

        .audio-player.active {
            display: block;
            animation: slideDown 0.4s ease;
        }

        .audio-player h3 {
            margin-bottom: 24px;
            color: #2d3748;
            font-size: 1.5rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .audio-player audio {
            width: 100%;
            margin-bottom: 20px;
            border-radius: 12px;
            outline: none;
        }

        .download-btn {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 14px 28px;
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
            text-decoration: none;
            border-radius: 12px;
            font-weight: 600;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 6px 20px rgba(72, 187, 120, 0.3);
        }

        .download-btn:hover {
            background: linear-gradient(135deg, #68d391 0%, #48bb78 100%);
            box-shadow: 0 10px 30px rgba(72, 187, 120, 0.4);
            transform: translateY(-2px);
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 12px;
        }

        ::-webkit-scrollbar-track {
            background: rgba(0, 0, 0, 0.5);
            border-radius: 10px;
        }

        ::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            border: 2px solid rgba(0, 0, 0, 0.5);
        }

        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        }

        /* Responsive */
        @media (max-width: 768px) {
            .title {
                font-size: 2.5rem;
            }

            .card {
                padding: 24px;
            }

            .btn-container {
                flex-direction: column;
            }

            .terminal {
                width: 100%;
                margin-left: 0;
            }
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }

        .header h1 {
            font-size: 3rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .header p {
            font-size: 1.2rem;
            opacity: 0.9;
        }

        .card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }

        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }

        .input-group input {
            flex: 1;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1rem;
            transition: border 0.3s;
        }

        .input-group input:focus {
            outline: none;
            border-color: #667eea;
        }

        .btn {
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        .terminal {
            background: #1e1e1e;
            border-radius: 10px;
            padding: 20px;
            font-family: 'Courier New', monospace;
            color: #00ff00;
            font-size: 1.1rem;
            min-height: 546px;
            max-height: 728px;
            overflow-y: auto;
            margin-bottom: 20px;
            display: none;
            width: 130%;
            margin-left: -15%;
        }

        .terminal.active {
            display: block;
        }

        .terminal-line {
            margin-bottom: 5px;
            white-space: pre-wrap;
            word-break: break-all;
        }

        .terminal-input {
            display: none;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
        }

        .terminal-input.active {
            display: flex;
        }

        .numpad {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            max-width: 600px;
        }

        .numpad-btn {
            padding: 15px;
            background: linear-gradient(135deg, #00ff00 0%, #00cc00 100%);
            color: #1e1e1e;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            font-size: 1.2rem;
            cursor: pointer;
            transition: all 0.3s;
            font-family: 'Courier New', monospace;
        }

        .numpad-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 255, 0, 0.4);
            background: linear-gradient(135deg, #00ff41 0%, #00dd00 100%);
        }

        .numpad-btn:active {
            transform: translateY(0);
        }

        .numpad-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        .file-info {
            background: #f5f5f5;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            display: none;
        }

        .file-info.active {
            display: block;
        }

        .file-info h3 {
            color: #333;
            margin-bottom: 15px;
        }

        .file-details {
            font-family: 'Courier New', monospace;
            background: #fff;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
        }

        .file-details p {
            margin: 8px 0;
            color: #555;
        }

        .file-details strong {
            color: #333;
        }

        .file-actions-row {
            display: flex;
            gap: 10px;
        }

        .delete-btn {
            padding: 10px 20px;
            background: #f44336;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: bold;
        }

        .delete-btn:hover {
            background: #d32f2f;
            box-shadow: 0 5px 15px rgba(244, 67, 54, 0.4);
        }

        /* ANSI Color Classes */
        .ansi-red { color: #ff0051; }
        .ansi-green { color: #00ff41; }
        .ansi-yellow { color: #ffff00; }
        .ansi-blue { color: #0099ff; }
        .ansi-magenta { color: #ff00ff; }
        .ansi-cyan { color: #00ffff; }
        .ansi-white { color: #ffffff; }
        .ansi-bold { font-weight: bold; }

        .audio-player {
            background: #f5f5f5;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            display: none;
        }

        .audio-player.active {
            display: block;
        }

        .audio-player h3 {
            margin-bottom: 15px;
            color: #333;
        }

        .audio-player audio {
            width: 100%;
            margin-bottom: 15px;
        }

        .download-btn {
            display: inline-block;
            padding: 10px 20px;
            background: #4caf50;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: background 0.3s;
        }

        .download-btn:hover {
            background: #45a049;
        }

        .status {
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 15px;
            text-align: center;
            font-weight: bold;
        }

        .status.info {
            background: #e3f2fd;
            color: #1976d2;
        }

        .status.success {
            background: #e8f5e9;
            color: #388e3c;
        }

        .status.error {
            background: #ffebee;
            color: #d32f2f;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .loading {
            animation: pulse 1.5s infinite;
        }

        ::-webkit-scrollbar {
            width: 10px;
        }

        ::-webkit-scrollbar-track {
            background: #2d2d2d;
        }

        ::-webkit-scrollbar-thumb {
            background: #00ff00;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo-container">
                <div class="logo-icon">🎵</div>
                <h1 class="title">YTMP3-DL</h1>
            </div>
            <p class="subtitle">Professional Audio Extraction System</p>
        </div>

        <div class="card glass input-section">
            <label class="input-label">🎯 YouTube URL</label>
            <div class="input-wrapper">
                <span class="input-icon">🔗</span>
                <input type="text" id="urlInput" class="url-input" placeholder="https://youtube.com/watch?v=..." />
            </div>
            <div class="btn-container">
                <button class="btn btn-primary" id="convertBtn" onclick="startConversion()">
                    <span class="btn-icon">⚡</span>
                    Start Conversion
                </button>
                <button class="btn btn-secondary" id="clearBtn">
                    <span class="btn-icon">🗑️</span>
                    Clear Queue
                </button>
            </div>
            <div id="status"></div>
        </div>

        <div class="card glass terminal-card">
            <h3 class="terminal-header-text">Terminal Output</h3>
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

        <div class="file-info glass" id="fileInfo">
            <h3>📁 File Information</h3>
            <div class="file-details" id="fileDetails"></div>
            <div class="file-actions-row">
                <button class="delete-btn" onclick="deleteFile()">
                    <span>🗑️</span>
                    Delete from Server
                </button>
            </div>
        </div>

        <div class="audio-player glass" id="audioPlayer">
            <h3>🎧 Your Audio is Ready!</h3>
            <audio controls id="audioElement"></audio>
            <a href="#" class="download-btn" id="downloadBtn" download>
                <span>⬇️</span>
                Download File
            </a>
        </div>
    </div>

    <script>
        const socket = io();
        let sessionId = null;
        let inputLocked = false;
        let currentFilename = null;

        socket.on('connect', () => {
            console.log('Connected to server');
        });

        socket.on('terminal_output', (data) => {
            const terminal = document.getElementById('terminal');
            const line = document.createElement('div');
            line.className = 'terminal-line';
            line.innerHTML = parseANSI(data.output);
            terminal.appendChild(line);
            terminal.scrollTop = terminal.scrollHeight;
            
            // Check if output is asking for input
            const text = data.output.toLowerCase();
            if (!inputLocked && (text.includes('select') || text.includes('[1-9]') || text.includes('»') || text.includes('quality'))) {
                setTimeout(() => {
                    document.getElementById('terminalInput').classList.add('active');
                }, 300);
            }
        });

        socket.on('request_input', (data) => {
            if (!inputLocked) {
                setTimeout(() => {
                    document.getElementById('terminalInput').classList.add('active');
                }, 500);
            }
        });

        socket.on('download_ready', (data) => {
            showStatus('Download complete! File ready.', 'success');
            document.getElementById('terminal').classList.remove('active');
            document.getElementById('terminalInput').classList.remove('active');
            inputLocked = false;
            currentFilename = data.filename;
            
            // Setup audio player
            const audioPlayer = document.getElementById('audioPlayer');
            const audioElement = document.getElementById('audioElement');
            const downloadBtn = document.getElementById('downloadBtn');
            
            audioElement.src = data.file_url;
            downloadBtn.href = data.file_url;
            downloadBtn.download = data.filename;
            
            audioPlayer.classList.add('active');
            
            // Show file info
            const fileInfo = document.getElementById('fileInfo');
            const fileDetails = document.getElementById('fileDetails');
            fileDetails.innerHTML = `
                <p><strong>📝 File Name:</strong> ${data.filename}</p>
                <p><strong>📍 Server Location:</strong> ${data.remote_path}</p>
                <p><strong>💾 Local Path:</strong> ${data.local_path}</p>
                <p><strong>📊 File Size:</strong> ${data.size}</p>
            `;
            fileInfo.classList.add('active');
            
            document.getElementById('convertBtn').disabled = false;
        });

        socket.on('file_deleted', (data) => {
            showStatus(data.message, 'success');
            document.getElementById('fileInfo').classList.remove('active');
            document.getElementById('audioPlayer').classList.remove('active');
            
            // Stop and clear audio
            const audioElement = document.getElementById('audioElement');
            audioElement.pause();
            audioElement.currentTime = 0;
            audioElement.src = '';
        });

        socket.on('error', (data) => {
            showStatus('Error: ' + data.message, 'error');
            document.getElementById('convertBtn').disabled = false;
            document.getElementById('terminal').classList.remove('active');
            document.getElementById('terminalInput').classList.remove('active');
            inputLocked = false;
        });

        function startConversion() {
            const url = document.getElementById('urlInput').value.trim();
            
            if (!url) {
                showStatus('Please enter a YouTube URL', 'error');
                return;
            }

            if (!url.includes('youtube.com') && !url.includes('youtu.be')) {
                showStatus('Please enter a valid YouTube URL', 'error');
                return;
            }

            document.getElementById('convertBtn').disabled = true;
            document.getElementById('audioPlayer').classList.remove('active');
            document.getElementById('fileInfo').classList.remove('active');
            document.getElementById('terminal').innerHTML = '';
            document.getElementById('terminal').classList.add('active');
            inputLocked = false;
            
            showStatus('Starting conversion...', 'info');
            
            sessionId = Date.now().toString();
            socket.emit('start_conversion', { url: url, session_id: sessionId });
        }

        function sendNumpad(value) {
            if (inputLocked) {
                return; // Prevent multiple inputs
            }

            // Lock input immediately
            inputLocked = true;

            // Disable all numpad buttons
            const buttons = document.querySelectorAll('.numpad-btn');
            buttons.forEach(btn => btn.disabled = true);
            
            // Echo the input to terminal
            const terminal = document.getElementById('terminal');
            const line = document.createElement('div');
            line.className = 'terminal-line';
            line.innerHTML = `<span class="ansi-cyan"><span class="ansi-bold">» ${value}</span></span>`;
            terminal.appendChild(line);
            terminal.scrollTop = terminal.scrollHeight;
            
            // Hide numpad after selection
            document.getElementById('terminalInput').classList.remove('active');
            
            // Send to backend
            socket.emit('terminal_input', { 
                session_id: sessionId, 
                input: value 
            });

            // Re-enable buttons after a delay (for next conversion)
            setTimeout(() => {
                buttons.forEach(btn => btn.disabled = false);
            }, 3000);
        }

        function deleteFile() {
            if (!currentFilename) {
                showStatus('No file to delete', 'error');
                return;
            }

            if (confirm(`Are you sure you want to delete "${currentFilename}" from the server?`)) {
                socket.emit('delete_file', { filename: currentFilename });
            }
        }

        function showStatus(message, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.innerHTML = `<div class="status ${type}">${message}</div>`;
        }

        function parseANSI(text) {
            // Strip all ANSI escape codes first, then re-add as HTML
            // Remove clear screen and cursor movement codes
            text = text.replace(/\033\[\d*[HJKABCDEFGST]/g, '');
            text = text.replace(/\033\[2J/g, '');
            text = text.replace(/\033\[\?25[hl]/g, '');
            text = text.replace(/\033\[\d+;\d+H/g, '');
            
            // Convert ANSI color codes to HTML spans
            text = text.replace(/\033\[91m/g, '<span class="ansi-red">');
            text = text.replace(/\033\[92m/g, '<span class="ansi-green">');
            text = text.replace(/\033\[93m/g, '<span class="ansi-yellow">');
            text = text.replace(/\033\[94m/g, '<span class="ansi-blue">');
            text = text.replace(/\033\[95m/g, '<span class="ansi-magenta">');
            text = text.replace(/\033\[96m/g, '<span class="ansi-cyan">');
            text = text.replace(/\033\[97m/g, '<span class="ansi-white">');
            text = text.replace(/\033\[1m/g, '<span class="ansi-bold">');
            text = text.replace(/\033\[0m/g, '</span>');
            text = text.replace(/\033\[5m/g, ''); // Remove blink
            
            // Handle any remaining escape codes
            text = text.replace(/\033\[\d+m/g, '</span>');
            
            return text;
        }

        // Handle keyboard input (1-9 and 0 for 10)
        document.addEventListener('DOMContentLoaded', () => {
            document.getElementById('urlInput').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    startConversion();
                }
            });

            // Keyboard shortcuts for numpad
            document.addEventListener('keydown', (e) => {
                if (inputLocked) return; // Don't accept input when locked

                const numpadActive = document.getElementById('terminalInput').classList.contains('active');
                if (numpadActive) {
                    if (e.key >= '1' && e.key <= '8') {
                        sendNumpad(e.key);
                        e.preventDefault();
                    }
                }
            });
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return HTML_TEMPLATE

@socketio.on('start_conversion')
def handle_conversion(data):
    url = data['url']
    session_id = data['session_id']
    client_id = request.sid  # Get unique client socket ID
    
    print(f"[+] Starting conversion for: {url} (Client: {client_id})")
    
    # Start the conversion in a separate thread
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
        
        # Only allow input from the client that started this session
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
        # Run the mp3.py script
        script_path = os.path.join(os.path.dirname(__file__), 'mp3.py')
        
        if not os.path.exists(script_path):
            socketio.emit('error', {'message': 'mp3.py not found!'}, room=client_id)
            return
        
        # Start the process with unbuffered output
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
            'client_id': client_id  # Store which client owns this session
        }
        
        # Read output character by character for immediate display
        output_buffer = ""
        while True:
            char = process.stdout.read(1)
            if not char:
                break
            
            output_buffer += char
            
            # Send line when newline is encountered - ONLY to the specific client
            if char == '\n':
                socketio.emit('terminal_output', {'output': output_buffer.rstrip()}, room=client_id)
                
                # Check if asking for input
                lower_buffer = output_buffer.lower()
                if ('select' in lower_buffer and '[1-9]' in lower_buffer) or \
                   ('»' in output_buffer) or \
                   ('enter' in lower_buffer and 'quality' in lower_buffer):
                    socketio.emit('request_input', {}, room=client_id)
                
                output_buffer = ""
        
        process.wait()
        
        # Download the file via SFTP
        print("[+] Conversion complete, fetching file...")
        socketio.emit('terminal_output', {'output': '\n[+] Fetching file from server...'}, room=client_id)
        
        time.sleep(1)  # Give the file time to finish writing
        downloaded_file = download_latest_file()
        
        if downloaded_file:
            socketio.emit('download_ready', {
                'filename': downloaded_file['name'],
                'file_url': f'/download/{downloaded_file["name"]}',
                'remote_path': os.path.join(SFTP_DIR, downloaded_file['name']),
                'local_path': os.path.join(os.getcwd(), 'downloads', downloaded_file['name']),
                'size': format_size(downloaded_file['size'])
            }, room=client_id)
        else:
            socketio.emit('error', {'message': 'Failed to download file from server'}, room=client_id)
        
        # Cleanup
        if session_id in active_processes:
            del active_processes[session_id]
            
    except Exception as e:
        print(f"[!] Error: {e}")
        socketio.emit('error', {'message': str(e)}, room=client_id)

def download_latest_file():
    """Download the most recent file from SFTP server"""
    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print(f"[+] Connecting to {SFTP_HOST}...")
        ssh.connect(SFTP_HOST, port=SFTP_PORT, username=SFTP_USER, password=SFTP_PASS)
        
        # Open SFTP session
        sftp = ssh.open_sftp()
        
        # List files in download directory
        files = []
        for item in sftp.listdir_attr(SFTP_DIR):
            if item.filename.endswith(('.mp3', '.flac', '.wav', '.m4a', '.opus')):
                files.append({
                    'name': item.filename,
                    'mtime': item.st_mtime,
                    'size': item.st_size
                })
        
        if not files:
            print("[!] No audio files found")
            sftp.close()
            ssh.close()
            return None
        
        # Get the most recent file
        latest = max(files, key=lambda x: x['mtime'])
        
        print(f"[+] Downloading: {latest['name']}")
        
        # Download to local storage
        local_path = os.path.join('downloads', latest['name'])
        os.makedirs('downloads', exist_ok=True)
        
        sftp.get(os.path.join(SFTP_DIR, latest['name']), local_path)
        
        print(f"[+] Downloaded: {latest['name']} ({latest['size']} bytes)")
        
        sftp.close()
        ssh.close()
        
        return latest
        
    except Exception as e:
        print(f"[!] SFTP Error: {e}")
        return None

def format_size(bytes):
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"

@socketio.on('delete_file')
def handle_delete_file(data):
    filename = data['filename']
    client_id = request.sid
    
    try:
        # Delete from local storage
        local_path = os.path.join('downloads', filename)
        if os.path.exists(local_path):
            os.remove(local_path)
            print(f"[+] Deleted local file: {filename}")
        
        # Delete from remote server via SFTP
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SFTP_HOST, port=SFTP_PORT, username=SFTP_USER, password=SFTP_PASS)
        sftp = ssh.open_sftp()
        
        remote_path = os.path.join(SFTP_DIR, filename)
        sftp.remove(remote_path)
        
        sftp.close()
        ssh.close()
        
        print(f"[+] Deleted remote file: {filename}")
        
        # Only send response to the client that requested deletion
        socketio.emit('file_deleted', 
                     {'message': f'Successfully deleted {filename} from server and local storage'},
                     room=client_id)
        
    except Exception as e:
        print(f"[!] Delete error: {e}")
        socketio.emit('error', {'message': f'Failed to delete file: {str(e)}'}, room=client_id)

@app.route('/download/<filename>')
def download_file(filename):
    """Serve downloaded audio file"""
    try:
        file_path = os.path.join('downloads', filename)
        if os.path.exists(file_path):
            # Get proper MIME type for audio files
            mime_type = 'audio/mpeg'  # default
            if filename.endswith('.m4a'):
                mime_type = 'audio/mp4'
            elif filename.endswith('.flac'):
                mime_type = 'audio/flac'
            elif filename.endswith('.wav'):
                mime_type = 'audio/wav'
            elif filename.endswith('.opus'):
                mime_type = 'audio/opus'
            
            return send_file(file_path, mimetype=mime_type, as_attachment=False)
        else:
            return "File not found", 404
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   YTMP3-DL WEB TERMINAL SERVER                                ║
║   Running on: http://localhost:1234                           ║
║                                                               ║
║   Features:                                                   ║
║   ✓ Live terminal output with ANSI colors                     ║
║   ✓ Interactive quality selection                             ║
║   ✓ Automatic SFTP file retrieval                             ║
║   ✓ Built-in audio player and download                        ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Create downloads directory
    os.makedirs('downloads', exist_ok=True)
    
    # Run the server
    socketio.run(app, host='0.0.0.0', port=1234, debug=False)