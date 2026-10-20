import json

import pytest

from common.events.event_base import EventBase


class SampleEvent(EventBase):
    name = "sample"
    topic = "sample-events"
    fields = [
        {"name": "event_id", "kafka_type": "string", "es_type": "keyword"},
        {"name": "query", "kafka_type": "string", "es_type": "text",
         "es_fields": {"keyword": {"type": "keyword"}}},
        {"name": "note", "kafka_type": ["null", "string"], "kafka_default": None, "es_type": "keyword"},
        {"name": "count", "kafka_type": "int", "kafka_default": 0, "es_type": "integer"},
    ]


class DerivedEvent(EventBase):
    name = "derived"
    topic = "derived-events"
    produced_by = "flink"


def test_to_schema_is_an_avro_record_named_after_the_event():
    schema = json.loads(SampleEvent.to_schema())
    assert schema["type"] == "record"
    assert schema["name"] == "sample"
    assert [f["name"] for f in schema["fields"]] == ["event_id", "query", "note", "count"]


def test_to_schema_only_adds_defaults_when_declared():
    fields = {f["name"]: f for f in json.loads(SampleEvent.to_schema())["fields"]}
    assert "default" not in fields["event_id"]
    assert fields["note"]["default"] is None  # an explicit None default is kept
    assert fields["count"]["default"] == 0


def test_es_mapping_adds_shared_timestamp_and_multi_fields():
    props = SampleEvent.to_es_mapping()["properties"]
    assert props["@timestamp"] == {"type": "date"}
    assert props["query"] == {"type": "text", "fields": {"keyword": {"type": "keyword"}}}
    assert props["note"] == {"type": "keyword"}


def test_index_name_is_the_topic():
    assert SampleEvent.get_index_name() == "sample-events"


def test_defaults_for_optional_class_attributes():
    assert SampleEvent.weight == 1.0
    assert SampleEvent.domain == "other"
    assert SampleEvent.produced_by is None


def test_derived_events_cannot_be_generated():
    with pytest.raises(NotImplementedError, match="flink"):
        DerivedEvent.generate()
