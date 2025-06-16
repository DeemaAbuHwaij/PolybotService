import sqlite3
import json
from .base import StorageInterface
from decimal import Decimal


class SQLiteStorage(StorageInterface):
    def __init__(self, db_path="predictions.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                request_id TEXT PRIMARY KEY,
                original_path TEXT,
                predicted_path TEXT
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT,
                label TEXT,
                confidence REAL,
                bbox TEXT
            );
        """)
        self.conn.commit()

    def save_prediction(self, request_id, original_path, predicted_path):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO predictions (request_id, original_path, predicted_path) VALUES (?, ?, ?)",
            (request_id, original_path, predicted_path)
        )
        self.conn.commit()

    def save_detection(self, request_id, label, confidence, bbox):
        print(f"📝 Saving detection to DynamoDB: {request_id}")
        self.table.put_item(
            Item={
                "request_id": f"{request_id}#{label}",
                "type": "detection",
                "label": label,
                "confidence": Decimal(str(confidence)),  # ✅ Convert to Decimal
                "bbox": bbox,
                "parent_id": request_id
            }
        )

    def get_prediction(self, request_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT original_path, predicted_path FROM predictions WHERE request_id = ?",
            (request_id,)
        )
        row = cursor.fetchone()
        return {"original_path": row[0], "predicted_path": row[1]} if row else None
