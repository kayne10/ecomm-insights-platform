import random
from common.events import catalog
from common.events.event_base import EventBase

class SearchEvent(EventBase):
    name = "search"
    topic = "search-events"
    weight = 5
    domain = "browsing"

    fields = [
        {"name": "event_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "event_type", "kafka_type": "string", "es_type": "keyword"},
        {"name": "user_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "query", "kafka_type": "string", "es_type": "text", "es_fields": {"keyword": {"type": "keyword"}}},
        {"name": "filters", "kafka_type": {"type": "array", "items": "string"}, "es_type": "keyword"},
        {"name": "results_count", "kafka_type": "int", "es_type": "keyword"},
        {"name": "searched_at", "kafka_type": "string", "logicalType": "timestamp-millis", "es_type": "date"}
    ]

    @classmethod
    def generate(cls):
        sample_queries = ["laptop", "sneakers", "sofa", "headphones", "backpack", "yoga mat",
                          "lipstick", "lego", "desk lamp", "running shoes", "phone case", "blender"]
        return {
            "event_id": catalog.new_id(),
            "event_type": cls.name,
            "user_id": catalog.random_user(),
            "query": random.choice(sample_queries),
            "filters": random.sample(["brand:nike", "brand:apple", "color:red", "price:<100"], k=random.randint(0, 2)),
            "results_count": random.randint(0, 500),
            "searched_at": catalog.now_iso(),
        }
