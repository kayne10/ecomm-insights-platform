from events.add_to_cart import AddToCartEvent
from events.purchase import PurchaseEvent

# The registry is just a list of event classes
EVENT_REGISTRY = {
    "add_to_cart": AddToCartEvent,
    "purchase": PurchaseEvent,
}

