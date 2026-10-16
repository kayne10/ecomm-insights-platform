"""
Shared connection settings.

Defaults target the docker compose network. Override with environment variables
to run the apps from your laptop, e.g.:

    KAFKA_BOOTSTRAP_SERVERS=localhost:29092 \
    SCHEMA_REGISTRY_URL=http://localhost:8081 \
    ELASTICSEARCH_URL=http://localhost:9200 python main.py
"""
import os


class KafkaConfig:
    BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")


class SchemaRegistryConfig:
    URL = os.getenv("SCHEMA_REGISTRY_URL", "http://schema-registry:8081")


class ElasticsearchConfig:
    URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
