from common.events.add_to_cart import AddToCartEvent
from common.events.cart_abandoned import CartAbandonedEvent
from common.events.checkout_started import CheckoutStartedEvent
from common.events.product_review import ProductReviewEvent
from common.events.product_view import ProductViewEvent
from common.events.purchase import PurchaseEvent
from common.events.refund import RefundEvent
from common.events.remove_from_cart import RemoveFromCartEvent
from common.events.search import SearchEvent

# Maps the CLI/event name to its event class. Bootstrap creates a topic, schema,
# Elasticsearch alias and sink connector for every entry here.
EVENT_REGISTRY = {
    cls.name: cls
    for cls in [
        ProductViewEvent,
        SearchEvent,
        AddToCartEvent,
        RemoveFromCartEvent,
        CheckoutStartedEvent,
        PurchaseEvent,
        RefundEvent,
        ProductReviewEvent,
        # Derived (produced_by is set): emitted by the Flink job, never by the producer.
        CartAbandonedEvent,
    ]
}


# Event types the fake-data producer can generate.
GENERATED_EVENTS = {name: cls for name, cls in EVENT_REGISTRY.items() if cls.produced_by is None}
