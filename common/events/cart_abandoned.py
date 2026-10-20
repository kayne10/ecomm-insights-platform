from common.events.event_base import EventBase


class CartAbandonedEvent(EventBase):
    """
    Emitted by the Flink job in apps/flink-cart-abandonment when a checkout_started
    event has no purchase with the same cart_id within the abandonment timeout.

    This class is the single source of truth for the event's Avro schema: bootstrap
    registers it, and the Flink job reads it back from Schema Registry at startup.
    """

    name = "cart_abandoned"
    topic = "cart-abandoned-events"
    domain = "cart"
    produced_by = "flink"
    weight = 0

    fields = [
        {"name": "event_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "event_type", "kafka_type": "string", "es_type": "keyword"},
        {"name": "user_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "cart_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "product_ids", "kafka_type": {"type": "array", "items": "string"}, "es_type": "keyword"},
        {"name": "item_count", "kafka_type": "int", "es_type": "integer"},
        {"name": "cart_value", "kafka_type": "double", "es_type": "double"},
        {"name": "currency", "kafka_type": "string", "es_type": "keyword"},
        {"name": "checkout_at", "kafka_type": "string", "es_type": "date"},
        {"name": "timeout_seconds", "kafka_type": "long", "es_type": "long"},
        # When the cart was declared abandoned: checkout time + timeout (event time).
        {"name": "timestamp", "kafka_type": "string", "es_type": "date"},
    ]
