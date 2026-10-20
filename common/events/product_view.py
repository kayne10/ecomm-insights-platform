import random
from common.events import catalog
from common.events.event_base import EventBase

class ProductViewEvent(EventBase):
    name = "product_view"
    topic = "product-view-events"
    weight = 10
    domain = "browsing"

    fields = [
        {"name": "event_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "event_type", "kafka_type": "string", "es_type": "keyword"},
        {"name": "user_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "session_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "product_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "category", "kafka_type": "string", "es_type": "keyword"},
        {"name": "price", "kafka_type": "float", "es_type": "float"},
        {"name": "viewed_at", "kafka_type": "string", "logicalType": "timestamp-millis", "es_type": "keyword"}
    ]

    @classmethod
    def generate(cls):
        sku = catalog.random_sku()
        item = catalog.product(sku)
        return {
            "event_id": catalog.new_id(),
            "event_type": cls.name,
            "user_id": catalog.random_user(),
            "session_id": catalog.new_id(),
            "product_id": sku,
            "category": item["category"],
            "price": item["price"],
            "viewed_at": catalog.now_iso(),
        }
