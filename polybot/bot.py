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

class Bot:


    def __init__(self, token, telegram_chat_url, storage):
        self.storage = storage  # <- Store the injected storage backend
        self.telegram_bot_client = telebot.TeleBot(token)
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)

        # Get the path to certs/polybot.crt relative to this bot.py file
        cert_path = os.path.join(os.path.dirname(__file__), 'certs', 'polybot.crt')

        self.telegram_bot_client.set_webhook(
            url=f'{telegram_chat_url}/{token}/',
            certificate=open(cert_path, 'r'),
            timeout=60
        )

        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')


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

    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')


class QuoteBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        if msg["text"] != 'Please don\'t quote me':
            self.send_text_with_quote(msg['chat']['id'], msg["text"], quoted_msg_id=msg["message_id"])


def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True


class ImageProcessingBot(Bot):
    def __init__(self, token, telegram_chat_url):
        super().__init__(token, telegram_chat_url)
        self.media_group_photos = {}

    def handle_message(self, message):
        chat_id = None
        try:
            chat_id = message['chat']['id']

            # Handle /start and text
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
                                   "📥 To retrieve a saved prediction: `/get <message_id>`")
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

            # Handle photo
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

                # CONCAT MULTI-PHOTO
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
                        self.send_text(chat_id,
                                       "'Concat' requires 2 photos sent together. Try again please with 2 photos")
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

                            self.send_text(chat_id,
                                           f"{emoji_map['concat']} I am concatenating your photos *{direction}ly*. Just a few moments...")
                            img1 = Img(group['paths'][0])
                            img2 = Img(group['paths'][1])
                            img1.concat(img2, direction=direction)
                            output_path = img1.save_img()
                            self.send_photo(chat_id, output_path)
                            self.send_text(chat_id,
                                           f"💥 Your photos have been concatenated *{direction}ly* successfully!")
                            print(f"Processed and sent photo with filter 'concat {direction}'")
                        del self.media_group_photos[media_group_id]
                    return

                # SINGLE PHOTO FILTERS
                if not caption:
                    self.send_text(chat_id, "Please add a caption like 'Rotate', 'Blur', etc.")
                    return

                if caption == 'concat':
                    self.send_text(chat_id, "'Concat' requires 2 photos sent together. Try again please with 2 photos")
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

                # ⬅️ Add this block to save and send result for local filters
                if caption in ['blur', 'contour', 'rotate', 'segment', 'salt and pepper']:
                    output_path = img.save_img()
                    self.send_photo(chat_id, output_path)
                    self.send_text(chat_id, f"💥 Your photo has been *{caption}ed* successfully!")
                    print(f"Processed and sent photo with filter '{caption}'")
                    return
                elif caption == 'detect':
                    try:
                        output_path = img.save_img()
                        image_name = os.path.basename(output_path)

                        # Save prediction info
                        self.storage.save_prediction(
                            request_id=str(message["message_id"]),
                            original_path=local_photo_path,
                            predicted_path=str(output_path)
                        )

                        s3_key = f"{chat_id}/original/{image_name}"
                        bucket = os.getenv("AWS_S3_BUCKET")
                        if not bucket:
                            raise ValueError("❌ AWS_S3_BUCKET environment variable is not set.")

                        success = upload_file(output_path, bucket, s3_key)
                        if not success:
                            raise RuntimeError("❌ Upload to S3 failed")

                        yolo_url = os.getenv("YOLO_URL")
                        if not yolo_url:
                            raise ValueError("❌ YOLO_URL environment variable is not set.")

                        logger.info(f"📡 Sending detection request to YOLO: {yolo_url}")
                        response = requests.post(yolo_url, json={
                            "image_name": image_name,
                            "chat_id": chat_id
                        })
                        logger.info(f"✅ YOLO responded with: {response.status_code}, {response.text}")
                        response.raise_for_status()

                        data = response.json()
                        labels = data.get("labels", [])

                        # Save detections
                        for label in labels:
                            self.storage.save_detection(
                                request_id=str(message["message_id"]),
                                label=label,
                                confidence=1.0,  # placeholder
                                bbox="[]"  # placeholder
                            )

                        if labels:
                            reply_message = "🧠 Detected objects: " + ", ".join(labels)
                        else:
                            reply_message = "🔍 No objects detected."

                        self.send_text(chat_id, reply_message)
                        self.send_text(chat_id, "💥 Your photo has been *detected* successfully!")
                        return

                    except Exception as e:
                        logger.error("❌ Detection failed:")
                        logger.error(traceback.format_exc())
                        self.send_text(chat_id, "❗ Error occurred while contacting YOLO service.")
                        return



                else:
                    self.send_text(chat_id,
                                   "Unsupported filter! Try: Blur, Contour, Rotate, Segment, Salt and pepper, Detect, Concat.")
                    return


            else:
                self.send_text(chat_id, "Unsupported message type. Please send a photo with a caption.")

        except Exception as e:
            print("Error handling message:", traceback.format_exc())
            self.send_text(chat_id, "Something went wrong... please try again.")
