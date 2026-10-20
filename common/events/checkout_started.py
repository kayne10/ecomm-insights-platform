import random
from common.events import catalog
from common.events.event_base import EventBase


class CheckoutStartedEvent(EventBase):
    name = "checkout_started"
    topic = "checkout-started-events"
    weight = 1.5
    domain = "cart"

    fields = [
        {"name": "event_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "event_type", "kafka_type": "string", "es_type": "keyword"},
        {"name": "user_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "cart_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "product_ids", "kafka_type": {"type": "array", "items": "string"}, "es_type": "keyword"},
        {"name": "item_count", "kafka_type": "int", "es_type": "integer"},
        {"name": "cart_value", "kafka_type": "double", "es_type": "double"},
        {"name": "currency", "kafka_type": "string", "es_type": "keyword"},
        {"name": "timestamp", "kafka_type": "string", "es_type": "date"},
    ]

    @classmethod
    def generate(cls):
        skus = [catalog.random_sku() for _ in range(random.randint(1, 5))]
        return {
            "event_id": catalog.new_id(),
            "event_type": cls.name,
            "user_id": catalog.random_user(),
            "cart_id": catalog.new_id(),
            "product_ids": skus,
            "item_count": len(skus),
            "cart_value": round(sum(catalog.product(s)["price"] for s in skus), 2),
            "currency": "USD",
            "timestamp": catalog.now_iso(),
        }
