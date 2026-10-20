import random
from common.events import catalog
from common.events.event_base import EventBase

_REVIEWS = {
    5: [("Love it", "Exactly what I wanted, would buy again."), ("Excellent", "Great quality and fast shipping.")],
    4: [("Pretty good", "Works well, minor issues with packaging."), ("Solid", "Good value for the price.")],
    3: [("It's okay", "Does the job but nothing special."), ("Average", "Expected a bit more for the price.")],
    2: [("Disappointed", "Quality is lower than the photos suggest."), ("Meh", "Stopped working properly after a week.")],
    1: [("Terrible", "Arrived broken and support was unhelpful."), ("Do not buy", "Nothing like the description.")],
}


class ProductReviewEvent(EventBase):
    name = "product_review"
    topic = "product-review-events"
    weight = 0.5
    domain = "feedback"

    fields = [
        {"name": "event_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "event_type", "kafka_type": "string", "es_type": "keyword"},
        {"name": "user_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "product_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "category", "kafka_type": "string", "es_type": "keyword"},
        {"name": "rating", "kafka_type": "int", "es_type": "integer"},
        {"name": "title", "kafka_type": "string", "es_type": "text"},
        {"name": "body", "kafka_type": "string", "es_type": "text"},
        {"name": "verified_purchase", "kafka_type": "boolean", "es_type": "boolean"},
        {"name": "timestamp", "kafka_type": "string", "es_type": "date"},
    ]

    @classmethod
    def generate(cls):
        sku = catalog.random_sku()
        rating = random.choices([5, 4, 3, 2, 1], weights=[40, 25, 15, 10, 10])[0]
        title, body = random.choice(_REVIEWS[rating])
        return {
            "event_id": catalog.new_id(),
            "event_type": cls.name,
            "user_id": catalog.random_user(),
            "product_id": sku,
            "category": catalog.product(sku)["category"],
            "rating": rating,
            "title": title,
            "body": body,
            "verified_purchase": random.random() < 0.8,
            "timestamp": catalog.now_iso(),
        }
