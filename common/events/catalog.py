"""
Shared fake catalog so events reference the same customers and products.

Using a fixed pool (instead of a fresh uuid per event) lets Elasticsearch
aggregations answer questions like "top customers" or "most refunded product".
"""
import random
import uuid
from datetime import datetime, timezone

NUM_USERS = 2000
NUM_PRODUCTS = 500

# Real shops are skewed: a small group of loyal customers and bestselling products
# account for a large share of activity. This makes "top customers" and "top products"
# meaningful instead of a long tail of one-off ids.
LOYAL_USERS, LOYAL_SHARE = 100, 0.4
BESTSELLERS, BESTSELLER_SHARE = 40, 0.5
CATEGORIES = ["electronics", "fashion", "home", "toys", "sports", "beauty"]

# Deterministic per-product attributes, so a SKU always has the same price and category.
_rng = random.Random(42)
PRODUCTS = {
    f"sku-{1000 + i}": {
        "category": _rng.choice(CATEGORIES),
        "price": round(_rng.uniform(5, 500), 2),
    }
    for i in range(NUM_PRODUCTS)
}
_SKUS = list(PRODUCTS)


def new_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    """UTC timestamp in ISO-8601, parsed natively by Elasticsearch `date` fields."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def random_user() -> str:
    if random.random() < LOYAL_SHARE:
        return f"user-{random.randint(1, LOYAL_USERS)}"
    return f"user-{random.randint(1, NUM_USERS)}"


def random_sku() -> str:
    if random.random() < BESTSELLER_SHARE:
        return random.choice(_SKUS[:BESTSELLERS])
    return random.choice(_SKUS)


def product(sku: str) -> dict:
    return PRODUCTS[sku]
