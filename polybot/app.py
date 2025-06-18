import flask
from flask import request
import os
import json
from loguru import logger
from dotenv import load_dotenv

from polybot.bot import Bot, QuoteBot, ImageProcessingBot
from polybot.dynamodb_storage import DynamoDBStorage

# Load environment variables
load_dotenv(dotenv_path=f".env.{os.getenv('ENV', 'dev')}")

app = flask.Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
BOT_APP_URL = os.environ['BOT_APP_URL']

# ✅ Always use DynamoDB
storage = DynamoDBStorage()
storage.init()
logger.info("📦 Using DynamoDBStorage")

# Initialize bot
bot = ImageProcessingBot(TELEGRAM_BOT_TOKEN, BOT_APP_URL, storage)

@app.route('/', methods=['GET'])
def index():
    return 'Ok'

@app.route(f'/{TELEGRAM_BOT_TOKEN}/', methods=['POST'])
def webhook():
    try:
        req = request.get_json()
        logger.info(f"🔔 Incoming webhook:\n{json.dumps(req, indent=2)}")

        if 'message' not in req:
            logger.warning("⚠️ Webhook received without 'message' key")
            return 'ignored', 200

        bot.handle_message(req['message'])
        return 'Ok', 200

    except Exception as e:
        logger.error(f"💥 Error in webhook: {e}")
        return 'error', 500

@app.route('/predictions/<prediction_id>', methods=['POST'])
def prediction(prediction_id):
    from polybot.dynamodb_storage import DynamoDBStorage
    storage = DynamoDBStorage()
    prediction = storage.get_prediction(prediction_id)

    if prediction:
        chat_id = prediction.get("chat_id")
        labels = prediction.get("labels", [])
        label_text = "🧠 Detected: " + ", ".join(labels) if labels else "😕 No objects detected."
        if chat_id:
            print(f"[INFO] Sending message to chat_id {chat_id} with labels: {labels}")
            bot.send_text(chat_id, label_text)
        return {"status": "ok"}
    else:
        return {"status": "error", "message": "Prediction not found"}, 404


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8443)
