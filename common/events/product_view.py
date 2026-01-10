from datetime import datetime
import random
import uuid
from common.events.event_base import EventBase

class ProductViewEvent(EventBase):
    name = "product_view"
    topic = "product-view-events"

    fields = [
        {"name": "event_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "event_type", "kafka_type": "string", "es_type": "keyword"},
        {"name": "user_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "session_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "product_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "category", "kafka_type": "string", "es_type": "keyword"},
        {"name": "price", "kafka_type": "float", "es_type": "float"},
        {"name": "viewed_at", "kafka_type": "string", "logicalType": "timestamp-millis", "es_type": "keyword"}
    ]

    @classmethod
    def generate(cls):
        return {
            "event_id": str(uuid.uuid4()),
            "event_type": cls.name,
            "user_id": f"user-{random.randint(1, 5000)}",
            "session_id": str(uuid.uuid4()),
            "product_id": f"prod-{random.randint(1000, 9999)}",
            "category": random.choice(["electronics", "fashion", "home", "toys"]),
            "price": round(random.uniform(10, 500), 2),
            "viewed_at": datetime.utcnow().isoformat(),
        }
