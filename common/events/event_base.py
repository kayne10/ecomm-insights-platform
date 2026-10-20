import json
from abc import ABC, abstractmethod


class EventBase(ABC):
    """
    Base class for all events
    """

    name = None
    topic = None
    fields = []  # subclasses override
    # Relative frequency when a producer streams several event types at once.
    # e.g. product views are far more common than refunds.
    weight = 1.0
    # Business area, used for grouped Elasticsearch search aliases (events-<domain>).
    domain = "other"

    def __init__(self):
        pass

    def generate(cls):
        """
        Subclasses implement fake event generation
        """
        pass

    @classmethod
    def get_index_name(cls):
        """
        Topic/Index name = lowercase class name
        """
        return cls.topic
    
    @classmethod
    def to_schema(cls):
        """Kafka Avro-like schema for serialization."""
        schema = {
            "type": "record",
            "name": cls.name,
            "fields": [
                {"name": f["name"], "type": f["kafka_type"]}
                for f in cls.fields
            ],
        }
        return json.dumps(schema, indent=2)

    @classmethod
    def to_es_mapping(cls):
        """
        Elasticsearch mapping generated from fields list.

        Every event also gets `@timestamp` (filled by the `events-enrich` ingest
        pipeline) so all event types share one time field for search and Kibana.
        A field may add `es_fields` for multi-fields, e.g. a keyword copy of a text field.
        """
        properties = {"@timestamp": {"type": "date"}}
        for f in cls.fields:
            prop = {"type": f["es_type"]}
            if "es_fields" in f:
                prop["fields"] = f["es_fields"]
            properties[f["name"]] = prop
        return {"properties": properties}
