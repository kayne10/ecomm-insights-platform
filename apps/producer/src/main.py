import argparse
import time
import random
import logging
from confluent_kafka import Producer
from common.registry import EVENT_REGISTRY
from settings import ProducerConfig, setup_logger

logger = setup_logger()

def stream(event_types, config: ProducerConfig, batch_flush: int = 10, interval: float = 1.0):
    producer = Producer(config.as_dict())
    logger.info(f"Starting producer for event types: {event_types}")

    count = 0
    try:
        while True:
            event_cls = random.choice(event_types)
            payload = event_cls.generate()
            topic = event_cls.topic

            producer.produce(
                topic,
                key=payload["event_id"],
                value=str(payload),
                callback=lambda err, msg: logger.error(err) if err else logger.debug(f"Delivered {msg.topic()}:{msg.partition()} @ {msg.offset()}")
            )
            producer.poll(0)

            count += 1
            if count % batch_flush == 0:
                producer.flush()
            
            logger.info(f"[{event_cls.name}] Produced: {payload}")
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Shutting down producer...")
    finally:
        producer.flush()
        logger.info("All messages flushed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=str, help="List of event types to stream", required=True)
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between messages")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        print("\n".join(EVENT_REGISTRY.keys()))
    elif args.events:
        selected_events = []
        for evt in args.events.split(','):
            if evt not in EVENT_REGISTRY:
                raise ValueError(f"Unknown event type: {evt}")
            selected_events.append(EVENT_REGISTRY[evt])

        config = ProducerConfig()
        stream(selected_events, config, interval=args.interval)
    else:
        parser.print_help()
