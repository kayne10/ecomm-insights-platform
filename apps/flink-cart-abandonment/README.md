# Flink cart abandonment

A Flink 2.2 DataStream job, written in Java 17, that turns checkouts without a purchase into `cart_abandoned` events.

```
checkout-started-events ─┐                      keyBy(cart_id)
                         ├─ KafkaSource ─ filter ─────────────── CartAbandonmentDetector ─ KafkaSink ─ cart-abandoned-events
purchase-events ─────────┘   (event time, 5 s out-of-orderness)    (state + event-time timers)              │
                                                                                                cart_abandoned_es_sink
                                                                                                          │
                                                                                                   Elasticsearch / Kibana
```

## How it decides a cart is abandoned

The job is keyed by `cart_id`, and each cart is tracked independently:

1. **`checkout_started`** stores the checkout in state and sets an event-time timer for `checkout time + ABANDONMENT_TIMEOUT`.
2. **`purchase` with the same `cart_id`** deletes the timer and the state. The cart converted.
3. **The timer fires** while the checkout is still pending. The job emits `cart_abandoned` with the user, products, cart value, checkout time and timeout.

Edge cases:

* **Out-of-order events.** The detector remembers a purchase for one timeout, so a checkout that arrives after its own purchase is not reported. Watermarks allow 5 seconds of disorder between the two topics.
* **Repeated checkout of the same cart.** The clock restarts.
* **Purchases without a `cart_id`**, such as one-click buys or records from before schema v2, are dropped before the detector.
* **Stale state.** State has a TTL of three timeouts as a safety net. Normal flows clear it explicitly.
* **Event time, not wall-clock time.** Timers fire when the watermark passes them, which requires new events. If the producer stops, the last carts are only reported once traffic resumes.

## Design choices

| Choice | Why |
|---|---|
| Schemas come from Schema Registry at startup | The Python event classes in `common/events` stay the single source of truth. `cart_abandoned` is defined in `common/events/cart_abandoned.py`, registered by bootstrap and read back here. |
| One `KafkaSource` for both topics | A single watermark strategy, with idleness so a quiet topic doesn't stall time. The deserializer picks the Avro reader and mapper by topic. |
| At-least-once sink plus deterministic `event_id` | The id is a name-based UUID of the cart, and it is also the Kafka key. The Elasticsearch sink uses that key as the document id, so redelivery overwrites instead of duplicating, without Kafka transactions. |
| Records for the model, with no Kryo | `FlinkTypeTest` fails if a model change makes Flink fall back to Kryo. That's why `CartAbandoned` stores the timeout as seconds rather than a `Duration`. |
| Starts at the latest offset when no offsets are committed | Older checkouts predate `cart_id` on purchases and would all look abandoned. Set `START_FROM_EARLIEST=true` to replay anyway. |
| Stable operator `uid`s | State can be restored from a savepoint after the topology changes. |

## Layout

```
src/main/java/com/ecomm/insights/abandonment/
  CartAbandonmentJob.java          entry point and topology
  config/JobConfig.java            settings from environment variables
  model/CartEvent.java             input: checkout or purchase
  model/CartAbandoned.java         output event
  detect/CartAbandonmentDetector   the keyed process function
  serde/                           Kafka/Avro (de)serialization, Schema Registry lookup
  time/EventTimes.java             ISO-8601 parsing and formatting
src/test/java/...                  unit tests; operator tests use Flink's test harness
src/test/resources/schemas/        Avro schemas exported from the Python event classes
```

## Configuration

Set these as environment variables on `flink-jobmanager` in `docker-compose.yml`. Durations use Flink syntax, such as `90 s`, `2 min` or `1 h`.

| Variable | Default |
|---|---|
| `ABANDONMENT_TIMEOUT` | `2 min` locally (compose); a real shop would use 15–60 min |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` |
| `SCHEMA_REGISTRY_URL` | `http://schema-registry:8081` |
| `CHECKOUT_TOPIC` / `PURCHASE_TOPIC` / `OUTPUT_TOPIC` | `checkout-started-events` / `purchase-events` / `cart-abandoned-events` |
| `CONSUMER_GROUP` | `flink-cart-abandonment` |
| `START_FROM_EARLIEST` | `false` |
| `MAX_OUT_OF_ORDERNESS` | `5 s` |
| `SOURCE_IDLE_TIMEOUT` | `30 s` |
| `CHECKPOINT_INTERVAL` | `30 s` |

The producer only completes carts younger than 45 seconds (`CART_MAX_AGE_SECONDS` in `common/events/catalog.py`). Keep the timeout above that, or purchases will arrive for carts already reported as abandoned.

## Develop

No local JDK is needed. Everything runs in containers from the repo root:

```bash
make flink-test     # compile, unit tests, formatting check (mvn verify)
make flink-format   # apply google-java-format (AOSP style)
make flink          # build the image (runs the tests again) and (re)start the job
make flink-status   # job state plus cartsAbandoned / cartsConverted counters
make flink-logs
```

The Flink web UI is at http://localhost:8082. Schema Registry already uses 8081 on the host.

With a local JDK 17 and Maven you can also run `mvn verify` in this directory.

Checkpoints go to `/tmp` inside the container, so a container restart resumes from the committed Kafka offsets but loses in-flight carts. Persisting state across restarts would need a checkpoint volume and job restore from it.
