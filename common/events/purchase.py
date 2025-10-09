import random
import uuid
from datetime import datetime
from common.events.event_base import EventBase

class PurchaseEvent(EventBase):
    name = "purchase"
    topic = "purchase-events"
    
    fields = [
        {"name": "event_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "event_type", "kafka_type": "string"}, "es_type": "keyword",
        {"name": "user_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "order_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "amount", "kafka_type": "float", "es_type": "float"},
        {"name": "currency", "kafka_type": "string", "es_type": "keyword"},
        {"name": "timestamp", "kafka_type": "string", "es_type": "keyword"},
    ]

    @classmethod
    def generate(cls):
        return {
            "event_id": str(uuid.uuid4()),
            "event_type": cls.name,
            "user_id": str(uuid.uuid4()),
            "order_id": str(uuid.uuid4()),
            "amount": round(random.uniform(10, 500), 2),
            "currency": random.choice(["USD", "EUR", "GBP"]),
            "timestamp": datetime.utcnow().isoformat(),
        }
