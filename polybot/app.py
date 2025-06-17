import flask
import requests
from flask import request
import os
import json
from loguru import logger
from dotenv import load_dotenv
from polybot.bot import Bot, QuoteBot, ImageProcessingBot
from polybot.storage.factory import get_storage

load_dotenv(dotenv_path=f".env.{os.getenv('ENV', 'dev')}")

app = flask.Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
BOT_APP_URL = os.environ['BOT_APP_URL']

# Initialize bot once globally
storage = get_storage()
bot = ImageProcessingBot(TELEGRAM_BOT_TOKEN, BOT_APP_URL, storage)


@app.route('/predictions/<prediction_id>', methods=['POST'])
def receive_callback(prediction_id):
    try:
        data = request.get_json()
        chat_id = data.get('chat_id')

        if not chat_id:
            logger.error("❌ chat_id missing in callback body")
            return 'Missing chat_id', 400

        yolo_url = os.getenv("YOLO_URL")  # Must point to your deployed YOLO (e.g., http://yolo-dev:8080)
        prediction_url = f"{yolo_url}/predictions/{prediction_id}"

        logger.info(f"📡 Fetching prediction from YOLO: {prediction_url}")
        response = requests.get(prediction_url)

        if response.status_code != 200:
            logger.error(f"❌ Failed to fetch prediction from YOLO: {response.text}")
            return 'Error fetching prediction', 500

        prediction = response.json().get("prediction", {})
        original_path = prediction.get("original_path", "N/A")
        predicted_path = prediction.get("predicted_path", "N/A")

        # Send result to user
        bot.send_text(chat_id, "🧠 Prediction complete!")
        bot.send_text(chat_id, f"🖼️ Original image: {original_path}")
        bot.send_text(chat_id, f"📸 Predicted image: {predicted_path}")

        return 'ok', 200

    except Exception as e:
        logger.error(f"❌ Callback error: {str(e)}")
        return 'error', 500


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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8443)