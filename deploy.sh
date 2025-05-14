#!/bin/bash

echo "🚀 Starting Polybot deployment..."

cd /home/ubuntu/polybot || {
  echo "❌ Could not cd into /home/ubuntu/polybot"
  exit 1
}

echo "📥 Pulling latest changes..."
git pull origin main

echo "🔁 Restarting Polybot service..."
sudo systemctl restart polybot.service

echo "✅ Deployment finished successfully!"
