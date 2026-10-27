#!/bin/bash
set -e

# =========================================
# KSIIPRN VPS Setup Script
# =========================================

if [ "$EUID" -eq 0 ]; then
  echo "[INFO] Running as root."
else
  echo "[INFO] Running as non-root user."
fi

echo "[STEP 1/6] Updating system packages..."
apt-get update
apt-get upgrade -y

echo "[STEP 2/6] Installing dependencies..."
apt-get install -y python3 python3-pip git curl ufw

APP_DIR="/opt/ksiiprn"
if [ ! -d "$APP_DIR" ]; then
  echo "[STEP 3/6] Cloning repository..."
  git clone https://github.com/zenosxwedi-oss/ksiiprn.git "$APP_DIR"
else
  echo "[STEP 3/6] Repository already exists. Skipping clone."
fi

cd "$APP_DIR"

if [ ! -f .env ]; then
  echo "[STEP 4/6] Creating .env from template..."
  cp .env.example .env
  echo "[WARN] Please edit /opt/ksiiprn/.env before starting the bot."
fi

echo "[STEP 5/6] Installing Python dependencies..."
python3 -m pip install -r requirements.txt

echo "[STEP 6/6] Making startup script executable..."
chmod +x run.sh

cat <<'EOF'

====================================
Setup complete.

Next steps:
1. Edit /opt/ksiiprn/.env
2. Start the bot: /opt/ksiiprn/run.sh
3. Or enable systemd service:
   sudo cp /opt/ksiiprn/ksiiprn.service /etc/systemd/system/ksiiprn.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now ksiiprn
   sudo systemctl status ksiiprn

Check logs:
  journalctl -u ksiiprn -f
====================================
EOF
