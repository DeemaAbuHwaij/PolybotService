import traceback
import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
from polybot.img_proc import Img
import requests
import logging
import boto3
from botocore.exceptions import ClientError
import uuid
import json


# SQS client (global)
sqs = boto3.client("sqs", region_name=os.getenv("AWS_REGION"))
SQS_QUEUE_URL = os.getenv("YOLO_SQS_QUEUE_URL")


class Bot:
    def __init__(self, token, telegram_chat_url, storage):
        self.storage = storage
        self.token = token
        self.telegram_bot_client = telebot.TeleBot(token)
        self.set_webhook()
        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def set_webhook(self):
        time.sleep(0.5)
        env = os.getenv("ENV", "development")
        base_url = os.getenv("BOT_APP_URL")
        full_url = f"{base_url}/{self.token}/"
        cert_path = os.getenv("CERT_PATH")

        self.telegram_bot_client.remove_webhook()
        if env == "production" and cert_path:
            logger.info(f"📡 Setting webhook with certificate to {full_url}")
            self.telegram_bot_client.set_webhook(
                url=full_url,
                certificate=open(cert_path, 'r'),
                timeout=60
            )
        else:
            logger.info(f"📡 Setting webhook without certificate to {full_url}")
            self.telegram_bot_client.set_webhook(
                url=full_url,
                timeout=60
            )

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        if not self.is_current_msg_photo(msg):
            raise RuntimeError("Message content of type 'photo' expected")

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        with open(file_info.file_path, 'wb') as photo:
            photo.write(data)

        return file_info.file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")
        self.telegram_bot_client.send_photo(chat_id, InputFile(img_path))


class QuoteBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        if msg["text"] != 'Please don\'t quote me':
            self.send_text_with_quote(msg['chat']['id'], msg["text"], quoted_msg_id=msg["message_id"])


def upload_file(file_name, bucket, object_name=None):
    if object_name is None:
        object_name = os.path.basename(file_name)

    s3_client = boto3.client('s3', region_name=os.getenv("AWS_REGION"))
    try:
        s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True


class ImageProcessingBot(Bot):
    def __init__(self, token, telegram_chat_url, storage):
        super().__init__(token, telegram_chat_url, storage)
        self.media_group_photos = {}

    def handle_message(self, message):
        chat_id = None
        try:
            chat_id = message['chat']['id']

            if 'text' in message:
                text = message['text'].strip().lower()
                if text == '/start':
                    self.send_text(chat_id,
                        "👋 Hi! I'm Deema's image bot.\n\n"
                        "📸 To apply filters, send one photo with one of the following captions:\n"
                        "• Blur\n• Contour\n• Rotate\n• Segment\n• Salt and pepper\n• Detect\n\n"
                        "🌗 To concatenate images, send two photos together with one of these captions:\n"
                        "• concat horizontal\n• concat vertical\n\n"
                        "Just type the filter name as the photo's caption.\n\n"
                        "📥 To retrieve a saved prediction: `/get <message_id>`"
                    )
                elif text.startswith('/get'):
                    parts = text.split()
                    if len(parts) != 2:
                        self.send_text(chat_id, "Usage: /get <message_id>")
                        return

                    request_id = parts[1]
                    prediction = self.storage.get_prediction(request_id)

                    if prediction:
                        self.send_text(chat_id, "🎯 Found your saved prediction:")
                        self.send_text(chat_id, f"🖼️ Original path: {prediction['original_path']}")
                        self.send_text(chat_id, f"📸 Processed path: {prediction['predicted_path']}")
                    else:
                        self.send_text(chat_id, "❌ No prediction found for this ID.")
                else:
                    self.send_text(chat_id,
                        "🖼️ Please send a photo with one of the following filter captions:\n"
                        "• 📸 Blur\n• ✏️ Contour\n• 🔄 Rotate\n• 🧩 Segment\n• 🧂🌶️ Salt and pepper\n• 🧠 Detect\n\n"
                        "🌗 *To concatenate two photos*, send them together with a caption:\n"
                        "• concat horizontal or concat vertical")
                return

            if 'photo' in message:
                caption = message.get('caption', '').strip().lower()
                media_group_id = message.get('media_group_id')
                local_photo_path = self.download_user_photo(message)

                emoji_map = {
                    'blur': '📸',
                    'contour': '✏️',
                    'rotate': '🔄',
                    'segment': '🧩',
                    'salt and pepper': '🧂🌶️',
                    'concat': '🌗',
                    'detect': '🧠'
                }

                if media_group_id:
                    if media_group_id not in self.media_group_photos:
                        self.media_group_photos[media_group_id] = {
                            'paths': [],
                            'caption': caption,
                            'chat_id': chat_id
                        }

                    group = self.media_group_photos[media_group_id]
                    group['paths'].append(local_photo_path)

                    if len(group['paths']) > 2:
                        self.send_text(chat_id, "'Concat' requires 2 photos sent together. Try again please.")
                        del self.media_group_photos[media_group_id]
                        return

                    if caption:
                        group['caption'] = caption

                    if len(group['paths']) == 2:
                        if group['caption'].startswith('concat'):
                            direction = 'horizontal'
                            parts = group['caption'].split()
                            if len(parts) > 1 and parts[1] in ['horizontal', 'vertical']:
                                direction = parts[1]

                            self.send_text(chat_id, f"{emoji_map['concat']} Concatenating *{direction}ly*...")

                            img1 = Img(group['paths'][0])
                            img2 = Img(group['paths'][1])
                            img1.concat(img2, direction=direction)
                            output_path = img1.save_img()
                            self.send_photo(chat_id, output_path)
                            self.send_text(chat_id,
                                           f"💥 Your photos have been concatenated *{direction}ly* successfully!")
                        del self.media_group_photos[media_group_id]
                    return

                if not caption:
                    self.send_text(chat_id, "Please add a caption like 'Rotate', 'Blur', etc.")
                    return

                if caption == 'concat':
                    self.send_text(chat_id, "'Concat' requires 2 photos sent together. Try again please.")
                    return

                img = Img(local_photo_path)

                if caption in emoji_map:
                    self.send_text(chat_id,
                                   f"{emoji_map[caption]} I am doing a {caption} for your photo. Just a few moments...")

                if caption == 'blur':
                    img.blur()
                elif caption == 'contour':
                    img.contour()
                elif caption == 'rotate':
                    img.rotate()
                elif caption == 'segment':
                    img.segment()
                elif caption == 'salt and pepper':
                    img.salt_n_pepper()

                if caption in ['blur', 'contour', 'rotate', 'segment', 'salt and pepper']:
                    output_path = img.save_img()
                    self.send_photo(chat_id, output_path)
                    self.send_text(chat_id, f"💥 Your photo has been *{caption}ed* successfully!")
                    return

                elif caption == 'detect':
                    try:
                        output_path = img.save_img()
                        image_name = os.path.basename(output_path)
                        prediction_id = str(uuid.uuid4())

                        # Save locally
                        self.storage.save_prediction(
                            request_id=prediction_id,
                            original_path=local_photo_path,
                            predicted_path=str(output_path)
                        )

                        bucket = os.getenv("AWS_S3_BUCKET")
                        if not bucket:
                            raise ValueError("❌ AWS_S3_BUCKET not set")

                        s3_key = f"{chat_id}/original/{image_name}"
                        if not upload_file(output_path, bucket, s3_key):
                            raise RuntimeError("❌ Upload to S3 failed")

                        # Send to SQS
                        sqs.send_message(
                            QueueUrl=SQS_QUEUE_URL,
                            MessageBody=json.dumps({
                                "request_id": prediction_id,
                                "chat_id": chat_id,
                                "image_url": f"https://{bucket}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{s3_key}",
                                "bucket": bucket
                            })
                        )

                        self.send_text(chat_id, "🧠 Image sent to YOLO. You'll receive results soon!")
                        return

                    except Exception:
                        logger.error("❌ Detection failed:")
                        logger.error(traceback.format_exc())
                        self.send_text(chat_id, "❗ Error occurred during detection.")
                        return

                else:
                    self.send_text(chat_id, "❌ Unsupported filter. Try: Blur, Contour, Rotate, Segment, Salt and pepper, Detect.")
                    return

            else:
                self.send_text(chat_id, "❗ Unsupported message type. Please send a photo with a caption.")

        except Exception as e:
            logger.error("❌ Exception while handling message:")
            logger.error(traceback.format_exc())
            self.send_text(chat_id, "Something went wrong. Please try again.")
