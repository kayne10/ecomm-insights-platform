import random
import uuid
from datetime import datetime
from common.events.event_base import EventBase


class AddToCartEvent(EventBase):
    name = "add_to_cart"
    topic = "add-to-cart-events"

    fields = [
        {"name": "event_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "event_type", "kafka_type": "string", "es_type": "keyword"},
        {"name": "user_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "product_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "quantity", "kafka_type": "int", "es_type": "integer"},
        {"name": "timestamp", "kafka_type": "string", "es_type": "keyword"},
    ]

    @classmethod
    def generate(cls):
        return {
            "event_id": str(uuid.uuid4()),
            "event_type": cls.name,
            "user_id": str(uuid.uuid4()),
            "product_id": f"sku-{random.randint(1000, 9999)}",
            "quantity": random.randint(1, 5),
            "timestamp": datetime.utcnow().isoformat(),
        }
