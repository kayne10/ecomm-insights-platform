import random
import uuid
from datetime import datetime
from common.events.event_base import EventBase

class PurchaseEvent(EventBase):
    name = "purchase"
    topic = "purchase-events"
    
    fields = [
        {"name": "event_id", "type": "string"},
        {"name": "user_id", "type": "string"},
        {"name": "order_id", "type": "string"},
        {"name": "amount", "type": "float"},
        {"name": "currency", "type": "string"},
        {"name": "timestamp", "type": "string"},
    ]

    @classmethod
    def generate(cls):
        return {
            "event_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "order_id": str(uuid.uuid4()),
            "amount": round(random.uniform(10, 500), 2),
            "currency": random.choice(["USD", "EUR", "GBP"]),
            "timestamp": datetime.utcnow().isoformat(),
        }
