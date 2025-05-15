#!/bin/bash

set -e

PROJECT_DIR="/home/deema/PycharmProjects/PolybotService"
SERVICE_FILE="polybot.service"
VENV_PATH="$PROJECT_DIR/venv"


# Create venv if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
  echo "🌀 Creating virtual environment..."
  python3 -m venv "$VENV_PATH"
fi

# Activate venv and install dependencies
echo "📦 Installing requirements..."
source "$VENV_PATH/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/polybot/requirements.txt"

# Copy systemd service file
echo "📁 Copying $SERVICE_FILE to systemd..."
sudo cp "$PROJECT_DIR/$SERVICE_FILE" /etc/systemd/system/

# Reload and restart systemd service
echo "🔁 Reloading and restarting Polybot service..."
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl restart polybot.service
sudo systemctl enable polybot.service

# Check if the service is running
if systemctl is-active --quiet polybot.service; then
  echo "✅ Polybot service is running!"
else
  echo "❌ Polybot service failed to start."
  sudo systemctl status polybot.service --no-pager
  exit 1
fi
