import copy
import json
import random
import time
import boto3
from uuid import uuid4
from collections import namedtuple
from argparse import ArgumentParser

Product = namedtuple('Product', ['code', 'name', 'price'])

products = [
    Product('A0001', 'Hair Comb', 2.99),
    Product('A0002', 'Toothbrush', 5.99),
    Product('A0003', 'Dental Floss', 0.99),
    Product('A0004', 'Hand Soap', 1.99)
]

customer_ids = [
    "C1000", "C1001", "C1002", "C1003", "C1004", "C1005", "C1006", "C1007", "C1008", "C1009",
    "C1010", "C1011", "C1012", "C1013", "C1014", "C1015", "C1016", "C1017", "C1018", "C1019",
]


def make_cartitems():
    """
    Generate random items in cart
    
    Returns: cart (list of dicts)
    """
    available_products = copy.copy(products)
    n_products = len(products)
    cart_items = []
    for _ in range(random.randint(1,n_products)):
        product = random.choice(available_products)
        available_products.remove(product)
        qty = random.randint(1, 10)
        
        cart_items.append({
            'product_name': product.name,
            'product_code': product.code,
            'product_quantity': qty,
            'product_price': product.price
        })

    return cart_items


def main(stream_duration):
    start_time = time.time()
    is_streaming = True
    while is_streaming:
        # Generate orders
        order = json.dumps({
            "order_id": str(uuid4()),
            "customer_id": random.choice(customer_ids),
            "cart_items": make_cartitems()
        })
        # For FileStreamSourceConnector, print order
        # For kafka.Producer class, send directly to topic
        print(order)
        time.sleep(0.3)
        stopwatch = time.time() - start_time
        if stopwatch >= stream_duration:
            is_streaming = False


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--stream-duration', type=int, default=60, required=False, help="Time to keep stream running for")
    args = parser.parse_args()
    main(args.stream_duration)
