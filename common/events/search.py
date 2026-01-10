from datetime import datetime
import random
import uuid
from common.events.event_base import EventBase

class SearchEvent(EventBase):
    name = "search"
    topic = "search-events"

    fields = [
        {"name": "event_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "event_type", "kafka_type": "string", "es_type": "keyword"},
        {"name": "user_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "query", "kafka_type": "string", "es_type": "text"},
        {"name": "filters", "kafka_type": {"type": "array", "items": "string"}, "es_type": "keyword"},
        {"name": "results_count", "kafka_type": "int", "es_type": "keyword"},
        {"name": "searched_at", "kafka_type": "string", "logicalType": "timestamp-millis", "es_type": "date"}
    ]

    @classmethod
    def generate(cls):
        sample_queries = ["laptop", "sneakers", "sofa", "headphones", "backpack"]
        return {
            "event_id": str(uuid.uuid4()),
            "event_type": cls.name,
            "user_id": f"user-{random.randint(1, 5000)}",
            "query": random.choice(sample_queries),
            "filters": random.sample(["brand:nike", "brand:apple", "color:red", "price:<100"], k=random.randint(0, 2)),
            "results_count": random.randint(0, 500),
            "searched_at": datetime.utcnow().isoformat(),
        }
