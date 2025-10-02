import random
import uuid
from datetime import datetime
from common.events.event_base import EventBase


class AddToCartEvent(EventBase):
    name = "add_to_cart"
    topic = "add-to-cart-events"

    fields = [
        {"name": "event_id", "type": "string"},
        {"name": "event_type", "type": "string"},
        {"name": "user_id", "type": "string"},
        {"name": "product_id", "type": "string"},
        {"name": "quantity", "type": "int"},
        {"name": "timestamp", "type": "string"},
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
