import boto3
from decimal import Decimal
from .base import StorageInterface

class DynamoDBStorage(StorageInterface):
    def __init__(self, table_name="deema-PolybotPredictions", region_name="us-west-1"):
        self.dynamodb = boto3.resource("dynamodb", region_name=region_name)
        self.table = self.dynamodb.Table(table_name)

    def save_prediction(self, request_id, original_path, predicted_path):
        print(f"📝 Saving prediction to DynamoDB: {request_id}")
        self.table.put_item(
            Item={
                "request_id": request_id,
                "type": "prediction",
                "original_path": original_path,
                "predicted_path": predicted_path
            }
        )

    def save_detection(self, request_id, label, confidence, bbox):
        print(f"📝 Saving detection to DynamoDB: {request_id}")

        # Convert bbox floats to Decimals
        bbox_decimal = [Decimal(str(coord)) for coord in bbox]

        self.table.put_item(
            Item={
                "request_id": f"{request_id}#{label}",
                "type": "detection",
                "label": label,
                "confidence": Decimal(str(confidence)),
                "bbox": bbox_decimal,
                "parent_id": request_id
            }
        )
    def get_prediction(self, request_id):
        response = self.table.get_item(
            Key={"request_id": request_id}
        )
        item = response.get("Item")
        if item:
            return {
                "original_path": item.get("original_path"),
                "predicted_path": item.get("predicted_path")
            }
        return None
