import os
import time
import requests
import telebot
from loguru import logger
from telebot.types import InputFile
import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv

load_dotenv()

class Bot:
    def __init__(self, token, telegram_chat_url):
        self.telegram_bot_client = telebot.TeleBot(token)
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)
        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        if not self.is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = 'photos'

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        file_path = os.path.join(folder_name, file_info.file_path.split('/')[-1])
        with open(file_path, 'wb') as photo:
            photo.write(data)

        return file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")

        self.telegram_bot_client.send_photo(chat_id, InputFile(img_path))

    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        try:
            if msg.get('text') == '/start':
                self.send_text(msg['chat']['id'], 'Bot is up and running!')
            elif self.is_current_msg_photo(msg):
                photo_path = self.download_user_photo(msg)
                self.send_text(msg['chat']['id'], 'Photo received. Processing...')

                s3_url = self.upload_photo_to_s3(photo_path)
                if s3_url:
                    self.send_text(msg['chat']['id'], 'Photo uploaded to S3.')
                    detection_results = self.send_detection_request(s3_url)
                    if detection_results:
                        self.send_detection_results(msg['chat']['id'], detection_results)
                    else:
                        self.send_text(msg['chat']['id'], 'Error processing image for object detection.')
                else:
                    self.send_text(msg['chat']['id'], 'Error uploading photo to S3.')
            else:
                self.send_text(msg['chat']['id'], 'Please send a photo or type /start to test the bot.')
        except Exception as e:
            logger.error(f'Error handling message: {e}')
            self.send_text(msg['chat']['id'], 'An error occurred while processing your request.')

    def upload_photo_to_s3(self, file_path):
        s3 = boto3.client('s3')
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        if not bucket_name:
            logger.error('S3_BUCKET_NAME environment variable is not set')
            return None
        object_name = os.path.basename(file_path)

        try:
            s3.upload_file
