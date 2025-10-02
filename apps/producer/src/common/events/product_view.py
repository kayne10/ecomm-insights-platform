from datetime import datetime
import random
import uuid
from common.events.event_base import EventBase

class ProductViewEvent(EventBase):
    name = "product_view"
    topic = "product-view-events"

    fields = [
        {"name": "event_id", "type": "string"},
        {"name": "user_id", "type": "string"},
        {"name": "session_id", "type": "string"},
        {"name": "product_id", "type": "string"},
        {"name": "category", "type": "string"},
        {"name": "price", "type": "float"},
        {"name": "viewed_at", "type": "string", "logicalType": "timestamp-millis"}
    ]

    @classmethod
    def generate(cls):
        return {
            "event_id": str(uuid.uuid4()),
            "user_id": f"user-{random.randint(1, 5000)}",
            "session_id": str(uuid.uuid4()),
            "product_id": f"prod-{random.randint(1000, 9999)}",
            "category": random.choice(["electronics", "fashion", "home", "toys"]),
            "price": round(random.uniform(10, 500), 2),
            "viewed_at": datetime.utcnow().isoformat(),
        }
