#!/bin/bash
set -e

PROJECT_DIR="$(pwd)"
SERVICE_FILE="polybot.service"
VENV_PATH="$PROJECT_DIR/venv"
ENV_FILE="$PROJECT_DIR/.env"

# Make sure python3-venv is installed
if ! python3 -m venv --help > /dev/null 2>&1; then
  echo "🧰 Installing python3-venv..."
  sudo apt update
  sudo apt install -y python3-venv
fi

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

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ .env file missing at $ENV_FILE"
  exit 1
fi

# Copy systemd service file
echo "⚙️ Copying $SERVICE_FILE to systemd..."
sudo cp "$PROJECT_DIR/$SERVICE_FILE" /etc/systemd/system/

# Reload and restart systemd service
echo "🔁 Reloading and restarting Polybot service..."
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl restart polybot.service
sudo systemctl enable polybot.service

# Check if service is running
if systemctl is-active --quiet polybot.service; then
  echo "✅ Polybot service is running!"
else
  echo "❌ Polybot service failed to start."
  sudo systemctl status polybot.service --no-pager
  exit 1
fi
