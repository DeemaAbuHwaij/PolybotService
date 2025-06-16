import os
from polybot.storage.sqlite_storage import SQLiteStorage
from polybot.storage.dynamodb_storage import DynamoDBStorage

def get_storage():
    storage_type = os.getenv("STORAGE_TYPE", "sqlite")

    if storage_type == "dynamodb":
        return DynamoDBStorage()
    else:
        return SQLiteStorage()
