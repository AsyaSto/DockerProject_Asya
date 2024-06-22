import time
from pathlib import Path
from flask import Flask, request, jsonify
from detect import run
import uuid
import yaml
from loguru import logger
import os
import boto3
import pymongo
import json
from bson import ObjectId  # Import ObjectId

images_bucket = os.environ['BUCKET_NAME']

with open("data/coco128.yaml", "r") as stream:
    names = yaml.safe_load(stream)['names']

app = Flask(__name__)

# Initialize MongoDB client
client = pymongo.MongoClient("mongodb://mongo1:27017/")
db = client["myappdb"]
collection = db["mycollection"]

# Custom JSON encoder to handle ObjectId
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super(JSONEncoder, self).default(obj)

app.json_encoder = JSONEncoder

@app.route('/predict', methods=['POST'])
def predict():
    prediction_id = str(uuid.uuid4())
    logger.info(f'prediction: {prediction_id}. start processing')

    # Extract the imgName from the JSON payload
    img_name = request.json.get('imgName')
    if not img_name:
        return "imgName parameter is required", 400

    s3 = boto3.client('s3')
    s3.download_file(images_bucket, img_name, 'local_image_path.jpg')

    original_img_path = 'local_image_path.jpg'
    logger.info(f'prediction: {prediction_id}/{original_img_path}. Download img completed')

    run(
        weights='yolov5s.pt',
        data='data/coco128.yaml',
        source=original_img_path,
        project='static/data',
        name=prediction_id,
        save_txt=True
    )

    logger.info(f'prediction: {prediction_id}/{original_img_path}. done')

    predicted_img_path = Path(f'static/data/{prediction_id}/{original_img_path}')
    s3.upload_file(str(predicted_img_path), images_bucket, f'predicted/{img_name}')

    pred_summary_path = Path(f'static/data/{prediction_id}/labels/{original_img_path.split(".")[0]}.txt')
    if pred_summary_path.exists():
        with open(pred_summary_path) as f:
            labels = f.read().splitlines()
            labels = [line.split(' ') for line in labels]
            labels = [{
                'class': names[int(l[0])],
                'cx': float(l[1]),
                'cy': float(l[2]),
                'width': float(l[3]),
                'height': float(l[4]),
            } for l in labels]

        logger.info(f'prediction: {prediction_id}/{original_img_path}. prediction summary:\n\n{labels}')

        prediction_summary = {
            'prediction_id': prediction_id,
            'original_img_path': original_img_path,
            'predicted_img_path': str(predicted_img_path),
            'labels': labels,
            'time': time.time()
        }

        collection.insert_one(prediction_summary)

        # Convert MongoDB ObjectId to string
        prediction_summary['_id'] = str(prediction_summary['_id'])

        return jsonify(prediction_summary)
    else:
        return f'prediction: {prediction_id}/{original_img_path}. prediction result not found', 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8081)