import random
from common.events import catalog
from common.events.event_base import EventBase


class RefundEvent(EventBase):
    name = "refund"
    topic = "refund-events"
    weight = 0.2
    domain = "orders"

    REASONS = ["damaged", "wrong_item", "not_as_described", "late_delivery", "changed_mind"]

    fields = [
        {"name": "event_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "event_type", "kafka_type": "string", "es_type": "keyword"},
        {"name": "user_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "order_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "product_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "category", "kafka_type": "string", "es_type": "keyword"},
        {"name": "amount", "kafka_type": "double", "es_type": "double"},
        {"name": "currency", "kafka_type": "string", "es_type": "keyword"},
        {"name": "reason", "kafka_type": "string", "es_type": "keyword"},
        {"name": "timestamp", "kafka_type": "string", "es_type": "date"},
    ]

    @classmethod
    def generate(cls):
        sku = catalog.random_sku()
        item = catalog.product(sku)
        return {
            "event_id": catalog.new_id(),
            "event_type": cls.name,
            "user_id": catalog.random_user(),
            "order_id": catalog.new_id(),
            "product_id": sku,
            "category": item["category"],
            "amount": item["price"],
            "currency": "USD",
            "reason": random.choice(cls.REASONS),
            "timestamp": catalog.now_iso(),
        }
