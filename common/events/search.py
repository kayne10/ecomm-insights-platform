from datetime import datetime
import random
import uuid
from common.events.event_base import EventBase

class SearchEvent(EventBase):
    name = "search"
    topic = "search-events"

    fields = [
        {"name": "event_id", "type": "string"},
        {"name": "event_type", "type": "string"},
        {"name": "user_id", "type": "string"},
        {"name": "query", "type": "string"},
        {"name": "filters", "type": {"type": "array", "items": "string"}},
        {"name": "results_count", "type": "int"},
        {"name": "searched_at", "type": "string", "logicalType": "timestamp-millis"}
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
