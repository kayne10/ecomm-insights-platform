from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka.schema_registry import SchemaRegistryClient, Schema
from common.registry import EVENT_REGISTRY
from common.settings import KafkaConfig, SchemaRegistryConfig

def create_topics():
    admin = AdminClient({"bootstrap.servers": KafkaConfig.BOOTSTRAP_SERVERS})

    topics = []
    for event_type, EventClass in EVENT_REGISTRY.items():
        topic_name = EventClass.get_index_name()
        topics.append(NewTopic(topic_name, num_partitions=1, replication_factor=1))

    fs = admin.create_topics(topics)
    for topic, f in fs.items():
        try:
            f.result()
            print(f"[Kafka] Created topic {topic}")
        except Exception as e:
            print(f"[Kafka] Failed to create topic {topic}: {e}")


def register_schemas():
    client = SchemaRegistryClient({"url": SchemaRegistryConfig.URL})

    for event_type, EventClass in EVENT_REGISTRY.items():
        schema_str = EventClass.get_avro_schema()
        schema = Schema(schema_str, "AVRO")
        subject = f"{EventClass.get_index_name()}-value"

        try:
            schema_id = client.register_schema(subject, schema)
            print(f"[SchemaRegistry] Registered {subject} (id={schema_id})")
        except Exception as e:
            print(f"[SchemaRegistry] Failed to register {subject}: {e}")

if __name__ == "__main__":
    create_topics()
    register_schemas()