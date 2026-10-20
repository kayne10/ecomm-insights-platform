import argparse
import time
import random
import json
import logging
from confluent_kafka import Producer
from confluent_kafka.serialization import MessageField, SerializationContext
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from common.registry import EVENT_REGISTRY, GENERATED_EVENTS
from common.settings import SchemaRegistryConfig
from settings import ProducerConfig, setup_logger

logger = setup_logger()

def stream(event_types, config: ProducerConfig, batch_flush: int = 10, interval: float = 1.0, limit: int = 0):
    schema_registry = SchemaRegistryClient({"url": SchemaRegistryConfig.URL})
    value_serializers = {
        event_cls: AvroSerializer(
            schema_registry,
            event_cls.to_schema(),
            lambda payload, ctx: payload,
        )
        for event_cls in event_types
    }
    producer = Producer(config.as_dict())
    logger.info(f"Starting producer for event types: {event_types}")

    # Weighted pick so a mixed stream looks like real traffic (many views, few refunds).
    weights = [event_cls.weight for event_cls in event_types]

    produced_count = 0
    try:
        while True:
            event_cls = random.choices(event_types, weights=weights)[0]
            payload = event_cls.generate()
            topic = event_cls.topic

            producer.produce(
                topic,
                key=payload["event_id"],
                value=value_serializers[event_cls](
                    payload,
                    SerializationContext(topic, MessageField.VALUE),
                ),
                callback=lambda err, msg: logger.error(err) if err else logger.debug(f"Delivered {msg.topic()}:{msg.partition()} @ {msg.offset()}")
            )
            producer.poll(0)

            produced_count += 1
            if produced_count % batch_flush == 0:
                producer.flush()
            
            logger.info(f"[{event_cls.name}] Produced: {json.dumps(payload)}")
            if limit and produced_count >= limit:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Shutting down producer...")
    finally:
        producer.flush()
        logger.info("All messages flushed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=str, help="Comma-separated event types to stream (or 'all')")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between messages")
    parser.add_argument("--count", type=int, default=0, help="Number of messages to produce; 0 streams forever")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        for name, cls in EVENT_REGISTRY.items():
            source = f"produced by {cls.produced_by}" if cls.produced_by else f"weight={cls.weight}"
            print(f"{name:<18} topic={cls.topic:<26} {source}")
    elif args.events:
        names = list(GENERATED_EVENTS) if args.events == "all" else [e.strip() for e in args.events.split(",") if e.strip()]
        selected_events = []
        for evt in names:
            if evt not in GENERATED_EVENTS:
                if evt in EVENT_REGISTRY:
                    parser.error(f"{evt} is produced by {EVENT_REGISTRY[evt].produced_by}, not by this producer")
                parser.error(f"Unknown event type: {evt}. Choose from: {', '.join(GENERATED_EVENTS)}")
            selected_events.append(EVENT_REGISTRY[evt])

        config = ProducerConfig()
        stream(selected_events, config, interval=args.interval, limit=args.count)
    else:
        parser.print_help()
