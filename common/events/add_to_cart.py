import random
import uuid
from datetime import datetime
from .event_base import EventBase


class AddToCartEvent(EventBase):
    fields = [
        {"name": "event_id", "type": "string"},
        {"name": "user_id", "type": "string"},
        {"name": "product_id", "type": "string"},
        {"name": "quantity", "type": "int"},
        {"name": "timestamp", "type": "string"},
    ]

    def generate_event(self):
        return {
            "event_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "product_id": f"sku-{random.randint(1000, 9999)}",
            "quantity": random.randint(1, 5),
            "timestamp": datetime.utcnow().isoformat(),
        }
