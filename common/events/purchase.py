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
        # Added after the original schema, so it must be optional to stay backward compatible.
        {"name": "cart_id", "kafka_type": ["null", "string"], "kafka_default": None, "es_type": "keyword"},
    ]

    # Share of purchases that complete an open checkout (the rest are e.g. one-click buys).
    CHECKOUT_SHARE = 0.9

    @classmethod
    def generate(cls):
        cart = catalog.take_open_cart() if random.random() < cls.CHECKOUT_SHARE else None
        return {
            "event_id": catalog.new_id(),
            "event_type": cls.name,
            "user_id": cart["user_id"] if cart else catalog.random_user(),
            "order_id": catalog.new_id(),
            "amount": cart["cart_value"] if cart else round(random.uniform(10, 500), 2),
            "currency": "USD",  # single currency so revenue sums are meaningful
            "timestamp": catalog.now_iso(),
            "cart_id": cart["cart_id"] if cart else None,
        }
