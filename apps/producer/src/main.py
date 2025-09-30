import argparse
import json
import time
from confluent_kafka import Producer
from common.registry import EVENT_REGISTRY
from settings import ProducerConfig, setup_logger


def delivery_report(err, msg):
    """
    Delivery callback called once for each produced message.
    """
    if err is not None:
        logger.error(f"Delivery failed for record {msg.key()}: {err}")
    else:
        logger.debug(
            f"Record successfully produced to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}"
        )


def stream(event_type: str, config: ProducerConfig, delay: float = 1.0, batch_flush: int = 10):
    """
    Stream fake events of a given type into Kafka with async batching.
    Flush every `batch_flush` messages to improve throughput.
    """
    if event_type not in EVENT_REGISTRY:
        raise ValueError(f"Unknown event_type: {event_type}. Available: {list(EVENT_REGISTRY.keys())}")

    EventClass = EVENT_REGISTRY[event_type]
    event = EventClass()

    producer = Producer(config.as_dict())
    topic = event.get_index_name()

    logger.info(f"Starting producer for event_type='{event_type}' on topic='{topic}'")

    count = 0
    try:
        while True:
            payload = event.generate_event()
            value = json.dumps(payload).encode("utf-8")

            producer.produce(topic, value=value, callback=delivery_report)

            # Poll for delivery callbacks
            producer.poll(0)

            count += 1
            if count % batch_flush == 0:
                producer.flush()  # flush every N messages

            logger.info(f"[{event_type}] Produced: {payload}")
            time.sleep(delay)

    except KeyboardInterrupt:
        logger.warning("Shutting down producer...")
    finally:
        producer.flush()
        logger.info("Final flush complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generic Kafka Event Producer")
    parser.add_argument("event_type", type=str, help="Type of event to produce (e.g., add_to_cart, purchase)")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between events in seconds")
    parser.add_argument("--batch-flush", type=int, default=10, help="Flush every N messages")
    args = parser.parse_args()

    logger = setup_logger("producer")

    stream(args.event_type, ProducerConfig, delay=args.delay, batch_flush=args.batch_flush)
