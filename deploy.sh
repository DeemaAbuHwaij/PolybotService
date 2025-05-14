#!/bin/bash

echo "🚀 Starting Polybot deployment..."

cd /home/ubuntu/polybot || {
  echo "❌ Failed to cd into /home/ubuntu/polybot"
  exit 1
}

echo "📥 Pulling latest code from main..."
git pull origin main

echo "🔁 Restarting polybot service..."
sudo systemctl restart polybot.service

echo "✅ Polybot deployed successfully!"
