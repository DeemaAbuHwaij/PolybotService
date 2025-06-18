import flask
from flask import request
import os
from polybot.bot import Bot, QuoteBot, ImageProcessingBot

import requests
app = flask.Flask(__name__)

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
TELEGRAM_CHAT_URL = os.environ['TELEGRAM_CHAT_URL']


@app.route('/', methods=['GET'])
def index():
    return 'Ok'

YOLO_URL = os.environ.get("YOLO_URL", "http://<YOLO_EC2_PRIVATE_IP>:8080")  # from .env

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


@app.route(f'/{TELEGRAM_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


if __name__ == "__main__":
    bot = ImageProcessingBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_URL)

    app.run(host='0.0.0.0', port=8443)