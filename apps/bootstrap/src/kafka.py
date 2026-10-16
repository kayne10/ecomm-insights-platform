"""Create Kafka topics and register Avro schemas. Safe to re-run."""
from confluent_kafka import KafkaError
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka.schema_registry import SchemaRegistryClient, Schema
from common.registry import EVENT_REGISTRY
from common.settings import KafkaConfig, SchemaRegistryConfig


def create_topics():
    admin = AdminClient({"bootstrap.servers": KafkaConfig.BOOTSTRAP_SERVERS})

    topics = [
        NewTopic(EventClass.get_index_name(), num_partitions=1, replication_factor=1)
        for EventClass in EVENT_REGISTRY.values()
    ]

    for topic, f in admin.create_topics(topics).items():
        try:
            f.result()
            print(f"[Kafka] Created topic {topic}")
        except Exception as e:
            err = e.args[0] if e.args else None
            if isinstance(err, KafkaError) and err.code() == KafkaError.TOPIC_ALREADY_EXISTS:
                print(f"[Kafka] Topic {topic} already exists")
            else:
                print(f"[Kafka] Failed to create topic {topic}: {e}")
                raise


def register_schemas():
    client = SchemaRegistryClient({"url": SchemaRegistryConfig.URL})

    for EventClass in EVENT_REGISTRY.values():
        schema = Schema(EventClass.to_schema(), "AVRO")
        subject = f"{EventClass.get_index_name()}-value"
        # Registering an identical schema is a no-op that returns the existing id.
        schema_id = client.register_schema(subject, schema)
        print(f"[SchemaRegistry] Registered {subject} (id={schema_id})")


if __name__ == "__main__":
    create_topics()
    register_schemas()
