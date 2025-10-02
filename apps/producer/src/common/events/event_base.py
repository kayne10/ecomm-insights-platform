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
