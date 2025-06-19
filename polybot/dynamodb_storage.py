import boto3
import os
import json
from decimal import Decimal
from loguru import logger
from pathlib import Path

class DynamoDBStorage:
    def __init__(self):
        self.table_name = os.getenv("DYNAMODB_TABLE", "deema-PolybotPredictions-dev")
        self.region = os.getenv("AWS_REGION", "us-west-1")
        self.dynamodb = boto3.resource("dynamodb", region_name=self.region)
        self.table = self.dynamodb.Table(self.table_name)

    def get_prediction(self, uid):
        try:
            response = self.table.get_item(Key={'uid': str(uid)})
            item = response.get('Item')
            if not item:
                logger.warning(f"[DynamoDB] No prediction found for uid: {uid}")
                return None

            detections = item.get("detections", [])
            labels = [d.get("label") for d in detections if "label" in d]

            original_image = Path(item.get("original_path", "")).name
            predicted_image = Path(item.get("predicted_path", "")).name

            logger.info(f"[DynamoDB] Retrieved prediction for uid: {uid}")
            logger.debug(f"[DynamoDB] Returning filenames: {original_image}, {predicted_image}")

            return {
                "prediction_uid": item.get("uid"),
                "original_image": original_image,
                "predicted_image": predicted_image,
                "labels": labels,
                "timestamp": item.get("created_at"),
                "chat_id": item.get("chat_id")
            }
        except Exception as e:
            logger.error(f"[ERROR] get_prediction failed: {e}")
            return None

    def init(self):
        pass
