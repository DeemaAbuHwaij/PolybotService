import boto3
import os
import json
from decimal import Decimal
from loguru import logger

class DynamoDBStorage:
    def __init__(self):
        self.table_name = os.getenv("DYNAMODB_TABLE", "deema-PolybotPredictions-dev")
        self.region = os.getenv("AWS_REGION", "us-west-1")
        self.dynamodb = boto3.resource("dynamodb", region_name=self.region)
        self.table = self.dynamodb.Table(self.table_name)

    def get_prediction(self, request_id):
        try:
            response = self.table.get_item(Key={'request_id': request_id})
            item = response.get('Item')
            if not item:
                logger.warning(f"[DynamoDB] No prediction found for request_id: {request_id}")
                return None

            detections = item.get("detections", [])
            labels = [d.get("label") for d in detections if "label" in d]

            logger.info(f"[DynamoDB] Retrieved prediction for request_id: {request_id}")

            return {
                "prediction_uid": item.get("request_id"),
                "original_image": item.get("original_path"),
                "predicted_image": item.get("predicted_path"),
                "labels": labels,
                "timestamp": item.get("created_at"),
                "chat_id": item.get("chat_id")
            }
        except Exception as e:
            logger.error(f"[ERROR] get_prediction failed: {e}")
            return None

    def init(self):
        pass
