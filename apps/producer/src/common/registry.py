from events.add_to_cart import AddToCartEvent
from events.purchase import PurchaseEvent
from events.product_view import ProductViewEvent
from events.search import SearchEvent

# The registry is just a list of event classes
EVENT_REGISTRY = {
    "add_to_cart": AddToCartEvent,
    "purchase": PurchaseEvent,
    "product_view": ProductViewEvent,
    "search": SearchEvent,
}

