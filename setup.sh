#!/bin/bash

# ============================================================
#  Setup Script — ytmp3-premium
# ============================================================

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# ── Helpers ──────────────────────────────────────────────────
info()    { echo -e "${CYAN}${BOLD}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}${BOLD}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}${BOLD}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}${BOLD}[ERROR]${RESET} $*" >&2; }

section() {
    echo ""
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${BOLD}  $*${RESET}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
}

check_command() { command -v "$1" &>/dev/null; }

# ── Confirm sudo access up front ─────────────────────────────
if ! sudo -v 2>/dev/null; then
    error "This script requires sudo privileges. Aborting."
    exit 1
fi

# Keep sudo alive for the duration of the script
( while true; do sudo -v; sleep 50; done ) &
SUDO_KEEPER_PID=$!
trap 'kill "$SUDO_KEEPER_PID" 2>/dev/null' EXIT

# ─────────────────────────────────────────────────────────────
section "1 / 5  System Package Update"
# ─────────────────────────────────────────────────────────────
info "Updating apt package list..."
if sudo apt update -y; then
    success "Package list updated."
else
    warn "apt update failed. Skipping and continuing with existing package list."
fi

# ─────────────────────────────────────────────────────────────
section "2 / 5  ffmpeg"
# ─────────────────────────────────────────────────────────────
if check_command ffmpeg; then
    FFMPEG_VER=$(ffmpeg -version 2>&1 | head -n1 | awk '{print $3}')
    success "ffmpeg already installed (${FFMPEG_VER}). Skipping."
else
    info "ffmpeg not found. Installing..."
    sudo apt install -y ffmpeg
    success "ffmpeg installed successfully."
fi

# ─────────────────────────────────────────────────────────────
section "3 / 5  Python Dependencies"
# ─────────────────────────────────────────────────────────────
info "Upgrading pip..."
pip install --upgrade pip -q

PACKAGES=(
    bcrypt
    bidict
    blinker
    certifi
    cffi
    charset-normalizer
    click
    cryptography
    Flask
    Flask-SocketIO
    ffmpeg
    h11
    idna
    invoke
    itsdangerous
    Jinja2
    MarkupSafe
    paramiko
    pycparser
    PyNaCl
    python-engineio
    python-socketio
    requests
    simple-websocket
    urllib3
    Werkzeug
    wsproto
)

info "Installing ${#PACKAGES[@]} Python packages..."
pip install -q "${PACKAGES[@]}"
success "Python packages installed."

info "Installing / upgrading yt-dlp..."
pip install -q -U yt-dlp
success "yt-dlp up to date."

# ─────────────────────────────────────────────────────────────
section "4 / 5  Output Directory"
# ─────────────────────────────────────────────────────────────
OUTPUT_DIR="$HOME/ytmp3-premium/music-output"
if [ -d "$OUTPUT_DIR" ]; then
    success "Directory already exists: ${OUTPUT_DIR}"
else
    mkdir -p "$OUTPUT_DIR"
    success "Created directory: ${OUTPUT_DIR}"
fi

# ─────────────────────────────────────────────────────────────
section "5 / 5  Cloudflare Tunnel (cloudflared)"
# ─────────────────────────────────────────────────────────────
if check_command cloudflared; then
    CF_VER=$(cloudflared --version 2>&1 | awk '{print $3}')
    success "cloudflared already installed (${CF_VER}). Skipping."
else
    info "cloudflared not found. Setting up Cloudflare apt repo..."

    # GPG keyring
    sudo mkdir -p --mode=0755 /usr/share/keyrings
    curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg \
        | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
    success "GPG key added."

    # Apt source (use the stable channel only — avoid duplicate entries)
    echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared noble main' \
        | sudo tee /etc/apt/sources.list.d/cloudflared.list >/dev/null
    success "Apt source configured."

    info "Installing cloudflared..."
    sudo apt-get update -q && sudo apt-get install -y cloudflared
    success "cloudflared installed successfully."
fi

# ─────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}${BOLD}║           ✅  Setup Complete!                    ║${RESET}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  Start the app with:  ${CYAN}${BOLD}python web-conv.py${RESET}"
echo ""
