import random
from common.events import catalog
from common.events.event_base import EventBase


class AddToCartEvent(EventBase):
    name = "add_to_cart"
    topic = "add-to-cart-events"
    weight = 3
    domain = "cart"

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
            "event_id": catalog.new_id(),
            "event_type": cls.name,
            "user_id": catalog.random_user(),
            "product_id": catalog.random_sku(),
            "quantity": random.randint(1, 5),
            "timestamp": catalog.now_iso(),
        }
