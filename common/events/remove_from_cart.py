import random
from common.events import catalog
from common.events.event_base import EventBase


class RemoveFromCartEvent(EventBase):
    name = "remove_from_cart"
    topic = "remove-from-cart-events"
    weight = 1.5
    domain = "cart"

    fields = [
        {"name": "event_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "event_type", "kafka_type": "string", "es_type": "keyword"},
        {"name": "user_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "product_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "category", "kafka_type": "string", "es_type": "keyword"},
        {"name": "quantity", "kafka_type": "int", "es_type": "integer"},
        {"name": "timestamp", "kafka_type": "string", "es_type": "date"},
    ]

    @classmethod
    def generate(cls):
        sku = catalog.random_sku()
        return {
            "event_id": catalog.new_id(),
            "event_type": cls.name,
            "user_id": catalog.random_user(),
            "product_id": sku,
            "category": catalog.product(sku)["category"],
            "quantity": random.randint(1, 3),
            "timestamp": catalog.now_iso(),
        }
