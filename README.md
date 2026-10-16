# 🛒 E-commerce Data Insights Platform

This project is a local event streaming playground for experimenting with Kafka, Schema Registry, Kafka Connect and Elasticsearch, fed by producers that emit fabricated e-commerce events (like an online shop).

Imagine orders from an online e-commerce site get emitted to Kafka. This data architecture is designed to process and ingest web orders at scale in real time. The targeted data marts are highly reliable for quick data-driven insights on products and customers. Insights Dashboard provides reports on which customers spent the most and which products earned and sold the most.

## 🏗️ Architecture

```
 +-------------+     Avro      +--------------+    ES sink     +---------------+     +--------+
 | producer    | ------------> |    Kafka     | -------------> | Elasticsearch | --> | Kibana |
 | (fake data) |               | topic/event  |  Kafka Connect |  alias/event  |     |        |
 +-------------+               +--------------+                +---------------+     +--------+
        |                             |
        +------- Schema Registry -----+
```

| Service         | From your laptop          | From containers              |
|-----------------|---------------------------|------------------------------|
| Kafka           | `localhost:29092`         | `kafka:9092`                 |
| Schema Registry | http://localhost:8081     | http://schema-registry:8081  |
| Kafka Connect   | http://localhost:8083     | http://connect:8083          |
| Elasticsearch   | http://localhost:9200     | http://elasticsearch:9200    |
| Kibana          | http://localhost:5601     |                              |

## 📦 Quick start

Requirements: Docker (with ~6 GB RAM allotted), `make`, `jq`, `curl`. Optional, for monitoring: [`kafkactl`](https://deviceinsight.github.io/kafkactl/), `tmux`, `watch` and `lazydocker`:

```bash
brew install deviceinsight/packages/kafkactl tmux watch lazydocker
```

```bash
make dev        # start infra, wait for health, bootstrap topics/schemas/ES, apply connectors
make produce    # send 20 add_to_cart events
make es-count   # see them land in Elasticsearch
```

Run `make` with no arguments to list every target. The common ones:

| Command | What it does |
|---|---|
| `make up` / `make down` | Start (waiting for healthchecks) / stop the infrastructure |
| `make reset` | Wipe all containers **and volumes**, then start fresh |
| `make bootstrap` | Create topics, register schemas, create ES ILM policies, templates and write aliases. Safe to re-run. |
| `make sink` | Create or update every connector in `apps/connect/connectors/` |
| `make produce EVENTS=add_to_cart,search COUNT=50 INTERVAL=0.1` | Send a fixed number of events. `EVENTS=all` uses every event type. |
| `make stream EVENTS=all` | Produce forever (Ctrl-C to stop) |
| `make ps` / `make logs SVC=connect` | Service health / tail logs |
| `make connectors` / `make sink-status` | Connector states / full status with task stack traces |
| `make topics` / `make subjects` / `make tail TOPIC=search-events` | Inspect Kafka, Schema Registry and decoded Avro messages |
| `make es-indices` / `make es-count` | Inspect Elasticsearch |
| `make build` | Rebuild the Python images after changing a `requirements.txt` |

The `bin/` scripts are still available for finer control: `bin/bootstrap`, `bin/stream`, and `bin/kc` (Kafka Connect).

### Development loop

* Python code in `common/` and `apps/*/src/` is volume-mounted into the containers, so edits take effect on the next `make produce` / `make bootstrap` without a rebuild.
* `docker compose up -d` only starts infrastructure. `bootstrap` and `producer` are one-shot tools behind the `tools` compose profile and run via `docker compose run --rm`.
* Connection settings in `common/settings.py` read `KAFKA_BOOTSTRAP_SERVERS`, `SCHEMA_REGISTRY_URL` and `ELASTICSEARCH_URL`, so the apps can also run directly on your laptop against the laptop-side endpoints above.
* Set `LOG_LEVEL=DEBUG` on the producer to see per-message delivery reports.

## 🔭 Observing the whole pipeline

```bash
make dev        # once, if the stack isn't up
make observe    # or: bin/observe --events all --interval 0.2
```

This opens a tmux session called `ecomm-observe` with three windows:

```
 window "pipeline"              window "health"                window "docker"
+-------------+-------------+  +--------------------------+  +----------------+
| 1 producer  | 2 kafka     |  | kafka-connect ERROR/WARN |  |   lazydocker   |
+-------------+-------------+  +--------------------------+  |                |
| 3 sink lag  | 4 ES counts |  | container CPU / memory   |  |                |
+-------------+-------------+  +--------------------------+  +----------------+
```

Follow one event through the panes. It is produced in **1**, decoded from Kafka in **2**, lag in **3** rises then returns to 0, and the count in **4** goes up. The first pane where the event stops showing up is where the problem is. Only `add_to_cart` has a sink so far, so the other ES counts stay at 0.

| Option | Default | Purpose |
|---|---|---|
| `--events` / `EVENTS=` | `add_to_cart` | Event types to stream: a name, comma list, or `all` |
| `--interval` / `INTERVAL=` | `0.5` | Seconds between events |
| `--topic` / `TOPIC=` | `add-to-cart-events` | Topic shown in pane 2 |
| `--group` / `GROUP=` | `connect-add_to_cart_es_sink` | Consumer group shown in pane 3 |
| `--every` / `EVERY=` | `2` | Refresh rate of panes 3 and 4 |
| `--no-produce` | | Open the dashboard without starting the producer |

tmux keys (prefix is `Ctrl-b`): `prefix n`/`p` switches windows, `prefix z` zooms a pane, `prefix d` detaches and leaves everything running. The mouse works for selecting and resizing panes. Run `make observe` again to re-attach, and `make observe-kill` to close it all, including the producer.

Every pane is a normal make target, so you can also run any of them alone in your own shells:

| Command | Shows |
|---|---|
| `make stream EVENTS=all` | Producer output |
| `make kctl-follow TOPIC=...` | Messages arriving in Kafka |
| `make sink-lag-watch` | Sink consumer lag as a compact table (`make sink-lag` for one snapshot) |
| `make es-watch` | Elasticsearch document counts |
| `make connect-errors` | Kafka Connect ERROR/WARN lines only |
| `make stats` | CPU and memory per container |
| `make docker-ui` | lazydocker: logs, restarts and shells for every container |

For checking document contents rather than counts, open Kibana at http://localhost:5601 and create a data view on `add_to_cart*`. Discover then shows documents as they arrive.

## 📈 Monitoring with kafkactl

The repo ships a [`kafkactl.yml`](kafkactl.yml) with an `ecomm-local` context pointing at `localhost:29092` and the Schema Registry, so Avro messages are decoded to JSON. The `make kctl-*` targets always use it, so your personal kafkactl config is never touched.

| Command | What it shows |
|---|---|
| `make kctl-topics` | Every topic with partition count, replication factor and non-default configs |
| `make kctl-topic TOPIC=search-events` | Oldest/newest offset per partition, i.e. how many messages a topic holds |
| `make kctl-groups` | Consumer groups, their type and the topics they read |
| `make kctl-group GROUP=<name>` | Committed offset, lag and connected members for one group |
| `make kctl-lag` | Lag per partition for every consumer group |
| `make kctl-watch` | Live lag for `GROUP`, refreshed every `EVERY` seconds |
| `make kctl-consume TOPIC=purchase-events MAX=5` | The last `MAX` messages, with key and timestamp |
| `make kctl-follow TOPIC=purchase-events` | New messages as they arrive |

`GROUP` defaults to `connect-add_to_cart_es_sink`, the consumer group of the Elasticsearch sink. Kafka Connect names sink groups `connect-<connector name>`.

### Reading consumer lag

```
TOPIC                PARTITION  NEWEST_OFFSET  OLDEST_OFFSET  CONSUMER_OFFSET  LEAD  LAG
add-to-cart-events   0          24             0              14               14    10
```

* **NEWEST_OFFSET** is the offset the next produced message will get.
* **CONSUMER_OFFSET** is the last offset the group has *committed*.
* **LAG** is the difference, i.e. messages produced but not yet processed by the group.

A lag that keeps growing means the consumer is stuck or too slow; check `make sink-status`. A lag that briefly rises and returns to 0 is normal.
Kafka Connect commits sink offsets every 10 seconds here (`CONNECT_OFFSET_FLUSH_INTERVAL_MS` in `apps/connect/config/env`), so lag can trail Elasticsearch by up to that long.

To watch the sink catch up, pause it, produce, then resume:

```bash
curl -X PUT localhost:8083/connectors/add_to_cart_es_sink/pause
make produce COUNT=50
make kctl-group            # LAG = 50
curl -X PUT localhost:8083/connectors/add_to_cart_es_sink/resume
make kctl-watch            # LAG drains to 0
```

### Using kafkactl directly

Pass the repo config and context explicitly. kafkactl v5 stores the active context in a separate global file, so the `current-context` inside `kafkactl.yml` alone is not enough.

```bash
alias kk='kafkactl -C kafkactl.yml --context ecomm-local'

kk get topics
kk describe topic add-to-cart-events
kk get consumer-groups --topic add-to-cart-events
kk describe consumer-group connect-add_to_cart_es_sink --only-with-lag
kk consume search-events --from-beginning --max-messages 5 --exit
kk consume purchase-events --from-timestamp 2026-10-15T00:00:00Z --exit
kk reset consumer-group-offset <group> --topic <topic> --oldest --execute   # replay (stop the consumer first)
```

To use plain `kafkactl` anywhere, copy the `ecomm-local` context into `~/.config/kafkactl/config.yml` and run `kafkactl config use-context ecomm-local`.

## ⚙️ Layout

| Path | Purpose |
|---|---|
| `common/events/*.py` | Event classes: fields (Avro + ES types), topic, fake-data generator |
| `common/registry.py` | Registry of event names to classes |
| `common/settings.py` | Shared connection settings (env-overridable) |
| `apps/bootstrap/` | Creates topics, schemas and ES resources from the registry |
| `apps/producer/` | Streams generated events to Kafka as Avro |
| `apps/connect/connectors/*.json` | Kafka Connect connector configs (one file per connector) |
| `apps/connect/plugins/` | Elasticsearch sink connector jars |

## 🛠️ Adding new events

1. Create a class in `common/events/` that extends `EventBase`, with `name`, `topic`, `fields` and `generate()`.
2. Add it to `common/registry.py`.
3. Run `make bootstrap` to create its topic, schema, ES template and write alias.
4. To sink it to Elasticsearch, copy `apps/connect/connectors/add_to_cart.json`, change `name`, `topics` and `topic.to.external.resource.mapping` (`<topic>:<event name>`), then run `make sink`.

The sink writes to the alias created by bootstrap (`external.resource.usage: ALIAS_INDEX`), so documents go to the ILM-managed `<event>_v1-000001` index. Connector 15.x ignores the old `topic.index.map` setting and rejects topic-renaming transforms, so use the mapping setting above.

## 🎨 Example event (ProductView)

```python
class ProductViewEvent(EventBase):
    name = "product_view"
    topic = "product-view-events"

    fields = [
        {"name": "event_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "user_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "category", "kafka_type": "string", "es_type": "keyword"},
        {"name": "price", "kafka_type": "float", "es_type": "float"},
        # ...
    ]

    @classmethod
    def generate(cls):
        return {
            "event_id": str(uuid.uuid4()),
            "user_id": f"user-{random.randint(1, 5000)}",
            "category": random.choice(["electronics", "fashion", "home", "toys"]),
            "price": round(random.uniform(10, 500), 2),
            # ...
        }
```

## 🩺 Troubleshooting

* **A service never turns healthy.** Run `make ps`, then `make logs SVC=<name>`. Elasticsearch and Connect need the most memory.
* **Connector task is FAILED.** `make sink-status` shows the stack trace. Fix the JSON, then `make sink` and `bin/kc restart add_to_cart`.
* **Bootstrap fails on Elasticsearch after an alias was deleted manually.** Run `make reset` to start from clean volumes.
* **kafkactl hangs or reports `connection refused` on 9092.** Your context points at the container-internal port. Use `localhost:29092`.
* **Port already in use.** Another local Kafka/ES is running. Stop it, or change the left-hand port in `docker-compose.yml`.

## 🔮 Roadmap

* Sink connectors for purchase, product_view and search
* Add Postgres consumers
* Add Flink streaming jobs
* Add Grafana / Kibana dashboards for analytics
