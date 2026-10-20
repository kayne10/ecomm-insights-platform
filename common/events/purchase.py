import random
from common.events import catalog
from common.events.event_base import EventBase

class PurchaseEvent(EventBase):
    name = "purchase"
    topic = "purchase-events"
    weight = 1
    domain = "orders"
    
    fields = [
        {"name": "event_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "event_type", "kafka_type": "string", "es_type": "keyword"},
        {"name": "user_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "order_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "amount", "kafka_type": "float", "es_type": "float"},
        {"name": "currency", "kafka_type": "string", "es_type": "keyword"},
        {"name": "timestamp", "kafka_type": "string", "es_type": "keyword"},
    ]

    @classmethod
    def generate(cls):
        return {
            "event_id": catalog.new_id(),
            "event_type": cls.name,
            "user_id": catalog.random_user(),
            "order_id": catalog.new_id(),
            "amount": round(random.uniform(10, 500), 2),
            "currency": "USD",  # single currency so revenue sums are meaningful
            "timestamp": catalog.now_iso(),
        }
