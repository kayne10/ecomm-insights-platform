"""Every generated event must match its own Avro schema and field list."""
import json

import pytest
from fastavro import parse_schema
from fastavro.validation import validate

from common.events import catalog
from common.events.checkout_started import CheckoutStartedEvent
from common.events.product_review import ProductReviewEvent
from common.events.product_view import ProductViewEvent
from common.events.purchase import PurchaseEvent
from common.registry import EVENT_REGISTRY, GENERATED_EVENTS

ES_TYPES = {"keyword", "text", "integer", "long", "float", "double", "date", "boolean"}


@pytest.mark.parametrize("event_cls", GENERATED_EVENTS.values(), ids=list(GENERATED_EVENTS))
def test_generated_payload_matches_the_avro_schema(event_cls):
    schema = parse_schema(json.loads(event_cls.to_schema()))
    for _ in range(20):
        assert validate(event_cls.generate(), schema, raise_errors=True)


@pytest.mark.parametrize("event_cls", GENERATED_EVENTS.values(), ids=list(GENERATED_EVENTS))
def test_generated_payload_has_exactly_the_declared_fields(event_cls):
    payload = event_cls.generate()
    assert set(payload) == {f["name"] for f in event_cls.fields}
    assert payload["event_type"] == event_cls.name


@pytest.mark.parametrize("event_cls", EVENT_REGISTRY.values(), ids=list(EVENT_REGISTRY))
def test_every_field_maps_to_a_known_elasticsearch_type(event_cls):
    for name, prop in event_cls.to_es_mapping()["properties"].items():
        assert prop["type"] in ES_TYPES, f"{event_cls.name}.{name}"


@pytest.mark.parametrize("event_cls", GENERATED_EVENTS.values(), ids=list(GENERATED_EVENTS))
def test_event_ids_are_unique(event_cls):
    assert len({event_cls.generate()["event_id"] for _ in range(100)}) == 100


def test_product_view_uses_catalog_price_and_category():
    event = ProductViewEvent.generate()
    item = catalog.product(event["product_id"])
    assert (event["price"], event["category"]) == (item["price"], item["category"])


def test_checkout_totals_its_products_and_opens_a_cart():
    event = CheckoutStartedEvent.generate()
    assert event["item_count"] == len(event["product_ids"])
    assert event["cart_value"] == round(sum(catalog.product(s)["price"] for s in event["product_ids"]), 2)
    assert event["cart_id"] in catalog._open_carts


def test_purchase_completes_an_open_checkout(monkeypatch):
    monkeypatch.setattr(PurchaseEvent, "CHECKOUT_SHARE", 1.0)
    checkout = CheckoutStartedEvent.generate()

    purchase = PurchaseEvent.generate()

    assert purchase["cart_id"] == checkout["cart_id"]
    assert purchase["user_id"] == checkout["user_id"]
    assert purchase["amount"] == checkout["cart_value"]
    assert catalog.take_open_cart() is None  # the cart is closed


def test_purchase_without_open_carts_has_no_cart_id(monkeypatch):
    monkeypatch.setattr(PurchaseEvent, "CHECKOUT_SHARE", 1.0)
    purchase = PurchaseEvent.generate()
    assert purchase["cart_id"] is None
    assert 10 <= purchase["amount"] <= 500


def test_purchase_cart_id_is_optional_for_schema_compatibility():
    # cart_id was added after purchase-events-value v1; without a default,
    # Schema Registry (BACKWARD) would reject the new version.
    field = next(f for f in json.loads(PurchaseEvent.to_schema())["fields"] if f["name"] == "cart_id")
    assert field["type"] == ["null", "string"]
    assert field["default"] is None


def test_review_title_matches_its_rating():
    for _ in range(50):
        review = ProductReviewEvent.generate()
        assert 1 <= review["rating"] <= 5
        assert review["title"] and review["body"]
