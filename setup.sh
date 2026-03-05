#!/bin/bash

echo "=== Updating system package list ==="
sudo apt update -y

echo "=== Checking for ffmpeg ==="
if ! command -v ffmpeg &> /dev/null
then
    echo "ffmpeg not found. Installing..."
    sudo apt install -y ffmpeg
else
    echo "ffmpeg already installed."
fi

echo "=== Installing Python dependencies ==="
pip install --upgrade pip

pip install \
    bcrypt \
    bidict \
    blinker \
    certifi \
    cffi \
    charset-normalizer \
    click \
    cryptography \
    Flask \
    Flask-SocketIO \
    ffmpeg \
    h11 \
    idna \
    invoke \
    itsdangerous \
    Jinja2 \
    MarkupSafe \
    paramiko \
    pycparser \
    PyNaCl \
    python-engineio \
    python-socketio \
    requests \
    simple-websocket \
    urllib3 \
    Werkzeug \
    wsproto

echo "=== Installing and upgrading yt-dlp ==="
pip install -U yt-dlp

echo "=== Creating music-output directory ==="
mkdir -p ~/ytmp3-premium/music-output

echo "=== Setup complete! ==="
