from common.events.add_to_cart import AddToCartEvent
from common.events.purchase import PurchaseEvent
from common.events.product_view import ProductViewEvent
from common.events.search import SearchEvent

# Maps the CLI/event name to its event class
EVENT_REGISTRY = {
    "add_to_cart": AddToCartEvent,
    "purchase": PurchaseEvent,
    "product_view": ProductViewEvent,
    "search": SearchEvent,
}
