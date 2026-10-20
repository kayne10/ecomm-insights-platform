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
    # Set to the producing system (e.g. "flink") for events derived from other events.
    # The fake-data producer never generates these; bootstrap still creates their topic,
    # schema, Elasticsearch resources and sink.
    produced_by = None

    def __init__(self):
        pass

    @classmethod
    def generate(cls):
        """
        Subclasses implement fake event generation
        """
        raise NotImplementedError(f"{cls.__name__} is produced by {cls.produced_by}, not generated")

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
            "fields": [cls._avro_field(f) for f in cls.fields],
        }
        return json.dumps(schema, indent=2)

    @staticmethod
    def _avro_field(f):
        """A field may set `kafka_default` (even None) to make it optional, which keeps
        a schema change backward compatible in Schema Registry."""
        field = {"name": f["name"], "type": f["kafka_type"]}
        if "kafka_default" in f:
            field["default"] = f["kafka_default"]
        return field

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
