import flask
from flask import request
import os
import json
from loguru import logger
from polybot.bot import Bot, QuoteBot, ImageProcessingBot

app = flask.Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
BOT_APP_URL = os.environ['BOT_APP_URL']

# Initialize bot once globally
bot = ImageProcessingBot(TELEGRAM_BOT_TOKEN, BOT_APP_URL)

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
