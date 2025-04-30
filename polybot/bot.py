import traceback
import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
from polybot.img_proc import Img



class Bot:

    def __init__(self, token, telegram_chat_url):
        # create a new instance of the TeleBot class.
        # all communication with Telegram servers are done using self.telegram_bot_client
        self.telegram_bot_client = telebot.TeleBot(token)

        # remove any existing webhooks configured in Telegram servers
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)

        # set the webhook URL
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)

        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        """
        Downloads the photos that sent to the Bot to `photos` directory (should be existed)
        :return:
        """
        if not self.is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

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

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')


class QuoteBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')

        if msg["text"] != 'Please don\'t quote me':
            self.send_text_with_quote(msg['chat']['id'], msg["text"], quoted_msg_id=msg["message_id"])


class ImageProcessingBot(Bot):
    def __init__(self, token, telegram_chat_url):
        super().__init__(token, telegram_chat_url) #Calls the parent class constructor (Bot) to initialize whatever it needs
        self.media_group_photos = {}  # media_group_id -> {'paths': [...], 'caption': '...', 'chat_id': ...}

    #Handling incoming Telegram messages
    def handle_message(self, message):
        chat_id = None
        try:
            chat_id = message['chat']['id']

            # Handle /start and plain text
            if 'text' in message:
                text = message['text'].strip().lower()  #Extracts the text, strips whitespace, and converts to lowercase.
                if text == '/start':
                    self.send_text(chat_id, "👋 Hello! I'm Deema's image bot. Send me a photo with a caption like 'Rotate', 'Blur', 'Segment', or send two photos with 'Concat' .")
                else:
                    self.send_text(
                        chat_id,
                        "🖼️ Please send a photo with one of the following filter captions:\n"
                        "• 📸 Blur\n"
                        "• ✏️ Contour\n"
                        "• 🔄 Rotate\n"
                        "• 🧩 Segment\n"
                        "• 🧂🌶️ Salt and pepper\n"
                        "• 🌗 Concat (send two photos at the same time)\n\n"
                        "Just type the filter name as the photo's caption."
                    )
                return

            # Handle photo messages
            if 'photo' in message:
                caption = message.get('caption', '').strip().lower() #Extracts the caption text, strips whitespace, and converts to lowercase.
                media_group_id = message.get('media_group_id')  #Checks if this photo is part of a media group - It’s used for concat.
                local_photo_path = self.download_user_photo(message)

                # Filter-to-emoji map
                emoji_map = {
                    'blur': '📸',
                    'contour': '✏️',
                    'rotate': '🔄',
                    'segment': '🧩',
                    'salt and pepper': '🧂🌶️',
                    'concat': '🌗'
                }

                # --- 2 PHOTOS FILTER (CONCAT) ---
                if media_group_id:  #Checks if the incoming photo is part of a media group
                    if media_group_id not in self.media_group_photos:
                        self.media_group_photos[media_group_id] = {   #nitializes a new group entry in the self.media_group_photos dictionary
                            'paths': [],
                            'caption': caption,
                            'chat_id': chat_id
                        }

                    # Adds the newly received photo's file path to the list of image paths in this group.
                    group = self.media_group_photos[media_group_id]
                    group['paths'].append(local_photo_path)

                    # More than 2 photos for concat || only one photo sent to concat
                    if len(group['paths']) > 2 :
                        self.send_text(chat_id,"'Concat' requires 2 photos sent together. Try again please with 2 photos")
                        del self.media_group_photos[media_group_id]
                        return


                    # Store the caption if it exists
                    if caption:
                        group['caption'] = caption

                    # Wait for 2 photos
                    if len(group['paths']) == 2:
                        if group['caption'] == 'concat':
                            self.send_text(chat_id, f"{emoji_map['concat']} I am concatenating your photos. Just a few moments...")
                            #Loads the two saved image files into Img objects using Img class.
                            img1 = Img(group['paths'][0])
                            img2 = Img(group['paths'][1])
                            img1.concat(img2, direction='horizontal')
                            output_path = img1.save_img()
                            self.send_photo(chat_id, output_path)
                            self.send_text(chat_id, f"💥 Your photos have been concatenated successfully!")
                            print(f"Processed and sent photo with filter concat'")
                        else:
                            self.send_text(chat_id, "Unsupported or missing caption for photo group.")

                        # Cleanup to prevents memory leaks and prepares the bot for the next media group.
                        del self.media_group_photos[media_group_id]
                    return


                # --- SINGLE PHOTO FILTERS ---
                if not caption:
                    self.send_text(chat_id, "Please add a caption like 'Rotate', 'Blur', etc.")
                    return

                if caption == 'concat':
                    self.send_text(chat_id, "'Concat' requires 2 photos sent together. Try again please with 2 photos")
                    return

                img = Img(local_photo_path)

                # Pre-message
                if caption in emoji_map:
                    self.send_text(chat_id, f"{emoji_map[caption]} I am doing a {caption} for your photo. Just a few moments...")

                # Apply filter
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
                else:
                    self.send_text(chat_id, "Unsupported filter! Try: Blur, Contour, Rotate, Segment, Salt and pepper, Concat.")
                    return

                # Post-processing
                output_path = img.save_img()
                self.send_photo(chat_id, output_path)
                self.send_text(chat_id, f"💥 Your photo has been {caption}ed successfully!")
                print(f"Processed and sent photo with filter '{caption}'")

            else:
                self.send_text(chat_id, "Unsupported message type. Please send a photo with a caption.")

        except Exception as e:
            print("Error handling message:", traceback.format_exc()) #It captures the error message + stack trace as a string,
            self.send_text(chat_id, "Something went wrong... please try again.")
