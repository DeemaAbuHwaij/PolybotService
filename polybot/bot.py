import os
import time
import json
import logging
import traceback
import boto3
import telebot
from botocore.exceptions import ClientError
from telebot.types import InputFile
from loguru import logger
from polybot.img_proc import Img


class Bot:
    def __init__(self, token, telegram_chat_url):
        self.token = token
        self.telegram_bot_client = telebot.TeleBot(token)
        self.set_webhook()
        logger.info(f"🤖 Telegram Bot info: {self.telegram_bot_client.get_me()}")

    def set_webhook(self):
        time.sleep(0.5)
        env = os.getenv("ENV", "development")
        base_url = os.getenv("BOT_APP_URL")
        full_url = f"{base_url}/{self.token}/"
        cert_path = os.getenv("CERT_PATH")

        self.telegram_bot_client.remove_webhook()
        if env == "production" and cert_path:
            logger.info(f"📡 Setting webhook with cert: {full_url}")
            self.telegram_bot_client.set_webhook(
                url=full_url,
                certificate=open(cert_path, 'r'),
                timeout=60
            )
        else:
            logger.info(f"📡 Setting webhook without cert: {full_url}")
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
            raise RuntimeError("Expected photo in message")

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
        logger.info(f"Incoming message: {msg}")
        if msg["text"] != "Please don't quote me":
            self.send_text_with_quote(msg['chat']['id'], msg["text"], quoted_msg_id=msg["message_id"])


def upload_file(file_name, bucket, object_name=None):
    if object_name is None:
        object_name = os.path.basename(file_name)

    s3_client = boto3.client('s3')
    try:
        s3_client.upload_file(file_name, bucket, object_name)
        return True
    except ClientError as e:
        logging.error(f"❌ S3 Upload Error: {e}")
        return False


def produce_message_to_sqs(message_body: dict, queue_url: str, region: str):
    sqs = boto3.client("sqs", region_name=region)
    try:
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body)
        )
        print(f"✅ Message sent to SQS. ID: {response['MessageId']}")
    except ClientError as e:
        print(f"❌ Failed to send message to SQS: {e}")


class ImageProcessingBot(Bot):
    def __init__(self, token, telegram_chat_url):
        super().__init__(token, telegram_chat_url)
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
                        "📸 Send a photo with one of these captions:\n"
                        "• Blur\n• Contour\n• Rotate\n• Segment\n• Salt and pepper\n• Detect\n\n"
                        "🌗 To concatenate images, send 2 photos together with one of these captions:\n"
                        "• concat horizontal\n• concat vertical"
                    )
                else:
                    self.send_text(chat_id,
                        "🖼️ Send a photo with one of the following filter captions:\n"
                        "• 📸 Blur\n• ✏️ Contour\n• 🔄 Rotate\n• 🧩 Segment\n• 🧂🌶️ Salt and pepper\n• 🧠 Detect\n\n"
                        "🌗 To concatenate two photos, send them together with a caption:\n"
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
                    group = self.media_group_photos.setdefault(media_group_id, {
                        'paths': [],
                        'caption': caption,
                        'chat_id': chat_id
                    })

                    group['paths'].append(local_photo_path)

                    if len(group['paths']) > 2:
                        self.send_text(chat_id, "❗ 'Concat' requires 2 photos sent together. Try again.")
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
                            self.send_text(chat_id, f"✅ Concatenated *{direction}ly* successfully!")
                        del self.media_group_photos[media_group_id]
                    return

                if not caption:
                    self.send_text(chat_id, "❗ Please add a caption like 'Rotate', 'Blur', etc.")
                    return

                if caption == 'concat':
                    self.send_text(chat_id, "❗ 'Concat' requires 2 photos sent together. Try again.")
                    return

                img = Img(local_photo_path)

                if caption in emoji_map:
                    self.send_text(chat_id,
                                   f"{emoji_map[caption]} Applying {caption} filter. Please wait...")

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
                    self.send_text(chat_id, f"✅ Your photo has been *{caption}ed* successfully!")
                    return

                elif caption == 'detect':
                    try:
                        output_path = img.save_img()
                        image_name = os.path.basename(output_path)
                        s3_key = f"{chat_id}/original/{image_name}"
                        bucket = os.getenv("AWS_S3_BUCKET")
                        region = os.getenv("AWS_REGION", "us-west-1")
                        queue_url = os.getenv("SQS_QUEUE_URL")

                        if not bucket or not queue_url:
                            raise ValueError("❌ Missing AWS_S3_BUCKET or SQS_QUEUE_URL")

                        if not upload_file(output_path, bucket, s3_key):
                            raise RuntimeError("❌ Upload to S3 failed")

                        produce_message_to_sqs(
                            {
                                "image_name": image_name,
                                "bucket_name": bucket,
                                "region_name": region,
                                "chat_id": chat_id,
                                "request_id": str(message["message_id"])
                            },
                            queue_url=queue_url,
                            region=region
                        )

                        self.send_text(chat_id, "🕐 Your image is being processed... please wait.")
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

        except Exception:
            logger.error("❌ Exception while handling message:")
            logger.error(traceback.format_exc())
            if chat_id:
                self.send_text(chat_id, "Something went wrong. Please try again.")
