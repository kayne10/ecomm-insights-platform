# 🛒 E-commerce Data Insights Platform

This project is a local event streaming playground for experimenting with Kafka, Schema Registry, and producers that emit fabricated e-commerce events (like an online shop).

You can spin up the stack in Docker Compose, bootstrap topics & schemas, and then run producers that generate realistic fake data into Kafka.

Imagine orders from a online e-commerice site get emitted to Kafka. This data architecture is designed to process and ingest web orders at scale in real time. The targeted data marts are highly reliable for quick data-driven insights on products and customers. Insights Dashboard provides reports on which customers spent the most and which products earned and sold the most.

## 🚀 Features

* Dockerized Kafka + Schema Registry (Confluent Platform)
* Producers that emit e-commerce events such as:
    * `AddToCartEvent`
    * `PurchaseEvent`
    * `ProductViewEvent`
    * `SearchEvent`

* Event schemas managed in Python classes
* CLI tool (`bin/stream`) for easy local workflows
    * `bootstrap` → create topics & register schemas
    * `produce` → run a producer for one or more event types
    * `status` → check running services
    * `logs` → tail producer logs

🏗️ Architecture

```
        +-------------------+
        |  Producer(s)      |   --> emits fabricated events
        +-------------------+
                 |
                 v
        +-------------------+
        |    Kafka Broker   |   --> topics per event type
        +-------------------+
                 |
         +-------+--------+
         |                |
+----------------+  +-----------------+
| SchemaRegistry |  | Consumers (WIP) |
+----------------+  +-----------------+
```

## 📦 Getting Started

📦 Getting Started
1. Clone the repo
```
git clone https://github.com/yourusername/ecommerce-event-streaming.git
cd ecommerce-event-streaming
```

2. Bootstrap the environment
```
./bin/stream bootstrap
```
➡️ Creates Kafka topics & registers schemas from common/event_registry.py.

3. Produce events

Emit events from a producer container:
```
# AddToCart only
./bin/stream produce add_to_cart

# Multiple event types
./bin/stream produce add_to_cart product_view search
```
Events are sent to their own Kafka topics (e.g. add_to_cart_events, product_view_events).

4. Check status
```
./bin/stream status
```

5. Tail logs
```
./bin/stream logs producer
```

## ⚙️ Configuration

* Kafka Producer config: defined in `producer/src/settings.py`
* Event schemas: defined in `common/events/*.py`
* Registry of events: `common/registry.py`

## 🛠️ Adding New Events

1. Create a new event class in `common/events/` that extends `EventBase`.
2. Define its `fields`, `topic`, and `generate()` method.
3. Add it to `common/registry.py`.

Re-run:
```
./bin/stream bootstrap
```
✅ New topic + schema are now available.

## 🎨 Example Event (ProductView)
```python
class ProductViewEvent(EventBase):
    name = "product_view"
    topic = "product_view_events"

    fields = [
        {"name": "event_id", "type": "string"},
        {"name": "event_type", "type": "string"},
        {"name": "user_id", "type": "string"},
        {"name": "session_id", "type": "string"},
        {"name": "product_id", "type": "string"},
        {"name": "category", "type": "string"},
        {"name": "price", "type": "float"},
        {"name": "viewed_at", "type": "string", "logicalType": "timestamp-millis"}
    ]

    @classmethod
    def generate(cls):
        return {
            "event_id": str(uuid.uuid4()),
            "event_type": cls.name,
            "user_id": f"user-{random.randint(1, 5000)}",
            "session_id": str(uuid.uuid4()),
            "product_id": f"prod-{random.randint(1000, 9999)}",
            "category": random.choice(["electronics", "fashion", "home", "toys"]),
            "price": round(random.uniform(10, 500), 2),
            "viewed_at": datetime.utcnow().isoformat(),
        }
```

## 🖼️ Screenshots / Output

When bootstrapped successfully:
```
🚀 Bootstrapping Kafka environment...

██████╗ ███████╗ █████╗ ██████╗ ██╗   ██╗    ███████╗ ██████╗ 
██╔══██╗██╔════╝██╔══██╗██╔══██╗╚██╗ ██╔╝    ██╔════╝██╔═══██╗
██████╔╝█████╗  ███████║██████╔╝ ╚████╔╝     █████╗  ██║   ██║
██╔═══╝ ██╔══╝  ██╔══██║██╔═══╝   ╚██╔╝      ██╔══╝  ██║   ██║
██║     ███████╗██║  ██║██║        ██║       ███████╗╚██████╔╝
╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝        ╚═╝       ╚══════╝ ╚═════╝ 

                  READY FOR INSIGHTS 🚀
```

## 🔮 Roadmap

* Add Elasticsearch + Postgres consumers
* Add Flink/Kafka Connect streaming jobs
* Add Grafana dashboards for analytics
* Add load generator mode (high-volume producers)