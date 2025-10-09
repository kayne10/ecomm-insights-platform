import json
from abc import ABC, abstractmethod


class EventBase(ABC):
    """
    Base class for all events
    """

    name = None
    topic = None
    fields = []  # subclasses override

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
    def get_avro_schema(cls):
        """
        Generate Avro schema dynamically from `fields`
        """
        schema = {
            "type": "record",
            "name": cls.__name__,
            "namespace": "com.example.ecommerce",
            "fields": cls.fields,
        }
        return json.dumps(schema, indent=2)
    
    @classmethod
    def to_schema(cls):
        """Kafka Avro-like schema for serialization."""
        return {
            "type": "record",
            "name": cls.name,
            "fields": [
                {"name": f["name"], "type": f["kafka_type"]}
                for f in cls.fields
            ],
        }

    @classmethod
    def to_es_mapping(cls):
        """Elasticsearch mapping generated from fields list."""
        return {
            "mappings": {
                "properties": {
                    f["name"]: {"type": f["es_type"]}
                    for f in cls.fields
                }
            }
        }
