#!/bin/bash

echo "🚀 Starting Polybot deployment..."

# ❌ This line causes the error
# cd /home/ubuntu/polybot

# ✅ Use a relative path instead (you're already inside ~/PolybotService)
cd polybot || {
  echo "❌ Could not cd into ./polybot"
  exit 1
}

# Example: restart or run something
# python bot.py &
echo "✅ Deployment complete"
