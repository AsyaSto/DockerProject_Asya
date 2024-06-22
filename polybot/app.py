import os
import flask
from flask import request
from bot import ObjectDetectionBot
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

app = flask.Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Access environment variables
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_APP_URL = os.environ.get('TELEGRAM_APP_URL')

# Ensure the environment variables are set
if not TELEGRAM_TOKEN or not TELEGRAM_APP_URL:
    raise ValueError("Please set TELEGRAM_TOKEN and TELEGRAM_APP_URL in the .env file")

@app.route('/', methods=['GET'])
def index():
    return 'Ok'

@app.route(f'/{TELEGRAM_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
    if 'message' in req:
        bot.handle_message(req['message'])
    else:
        logging.warning("Received a request without a message")
    return 'Ok'

if __name__ == "__main__":
    bot = ObjectDetectionBot(TELEGRAM_TOKEN, TELEGRAM_APP_URL)
    app.run(host='0.0.0.0', port=8443)
