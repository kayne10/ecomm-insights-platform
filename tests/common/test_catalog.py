import random
from datetime import datetime, timezone

from common.events import catalog


def test_products_have_fixed_price_and_category():
    sku = catalog.random_sku()
    item = catalog.product(sku)
    assert item["category"] in catalog.CATEGORIES
    assert 5 <= item["price"] <= 500
    assert catalog.product(sku) == item  # same SKU, same attributes


def test_catalog_is_identical_across_runs():
    # Seeded with a fixed RNG, so dashboards and tests see the same products every time.
    assert len(catalog.PRODUCTS) == catalog.NUM_PRODUCTS
    assert list(catalog.PRODUCTS)[0] == "sku-1000"


def test_users_and_skus_come_from_the_pools():
    for _ in range(200):
        assert 1 <= int(catalog.random_user().removeprefix("user-")) <= catalog.NUM_USERS
        assert catalog.random_sku() in catalog.PRODUCTS


def test_activity_is_skewed_towards_loyal_users_and_bestsellers():
    draws = 20_000
    loyal = sum(int(catalog.random_user()[5:]) <= catalog.LOYAL_USERS for _ in range(draws)) / draws
    bestsellers = set(list(catalog.PRODUCTS)[: catalog.BESTSELLERS])
    best = sum(catalog.random_sku() in bestsellers for _ in range(draws)) / draws

    # Uniform draws would give 5% and 8%; the skew pushes both well past their share.
    assert 0.40 < loyal < 0.47
    assert 0.50 < best < 0.58


def test_now_iso_is_utc_with_millisecond_precision():
    stamp = catalog.now_iso()
    parsed = datetime.fromisoformat(stamp)
    assert parsed.tzinfo == timezone.utc
    assert len(stamp.split(".")[1]) == len("123+00:00")


def test_new_ids_are_unique():
    assert len({catalog.new_id() for _ in range(1000)}) == 1000


def test_take_open_cart_returns_and_removes_a_cart():
    cart = {"cart_id": "c1", "user_id": "user-1"}
    catalog.open_cart(cart)

    assert catalog.take_open_cart() == cart
    assert catalog.take_open_cart() is None


def test_take_open_cart_is_none_without_carts():
    assert catalog.take_open_cart() is None


def test_carts_older_than_max_age_are_never_completed(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(catalog.time, "monotonic", lambda: now[0])
    catalog.open_cart({"cart_id": "old"})
    now[0] += catalog.CART_MAX_AGE_SECONDS + 1
    catalog.open_cart({"cart_id": "fresh"})

    assert catalog.take_open_cart()["cart_id"] == "fresh"
    assert catalog.take_open_cart() is None  # "old" was expired, not returned


def test_take_open_cart_picks_among_open_carts():
    for i in range(5):
        catalog.open_cart({"cart_id": f"c{i}"})
    random.seed(7)
    taken = {catalog.take_open_cart()["cart_id"] for _ in range(5)}
    assert taken == {f"c{i}" for i in range(5)}
