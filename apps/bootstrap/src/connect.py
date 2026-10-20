"""
Create or update one Elasticsearch sink connector per registered event. Safe to re-run.

Each connector reads the event's topic and writes to the event's ES write alias
(created by elastic.py), so documents land in the ILM-managed <event>_v1-NNNNNN index.
"""
import sys

import requests
from common.registry import EVENT_REGISTRY
from common.settings import ConnectConfig, ElasticsearchConfig, SchemaRegistryConfig


def connector_name(event_name: str) -> str:
    return f"{event_name}_es_sink"


def sink_config(event_cls) -> dict:
    return {
        "connector.class": "io.confluent.connect.elasticsearch.ElasticsearchSinkConnector",
        "tasks.max": "1",
        "topics": event_cls.topic,
        "connection.url": ElasticsearchConfig.URL,
        # Write to the alias bootstrap created instead of auto-creating an index named after the topic.
        # (Connector 15.x ignores topic.index.map and rejects topic-renaming SMTs.)
        "external.resource.usage": "ALIAS_INDEX",
        "topic.to.external.resource.mapping": f"{event_cls.topic}:{event_cls.name}",
        # Document _id = Kafka message key = event_id (set by the producer). Re-delivered or
        # replayed events overwrite themselves instead of duplicating, and wiping Kafka
        # (offsets restart at 0) can't overwrite older documents the way topic+partition+offset ids would.
        "key.ignore": "false",
        "schema.ignore": "true",  # mappings come from the ES index template
        "behavior.on.malformed.documents": "warn",
        "write.method": "insert",
        "max.buffered.records": "10000",
        "flush.timeout.ms": "60000",
        "value.converter": "io.confluent.connect.avro.AvroConverter",
        "value.converter.schema.registry.url": SchemaRegistryConfig.URL,
    }


def apply_sinks(only=None) -> bool:
    ok = True
    for name, event_cls in EVENT_REGISTRY.items():
        if only and name not in only:
            continue
        connector = connector_name(name)
        r = requests.put(
            f"{ConnectConfig.URL}/connectors/{connector}/config",
            json=sink_config(event_cls),
        )
        if r.ok:
            verb = "Created" if r.status_code == 201 else "Updated"
            print(f"[Connect] {verb} {connector} ({event_cls.topic} -> {name})")
        else:
            ok = False
            print(f"[Connect] Failed {connector}: {r.status_code} {r.text}")
    return ok


if __name__ == "__main__":
    # Optional args limit which events get a sink, e.g. `python connect.py refund search`
    sys.exit(0 if apply_sinks(set(sys.argv[1:]) or None) else 1)
