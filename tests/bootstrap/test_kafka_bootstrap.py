import json

import pytest
from confluent_kafka import KafkaError, KafkaException

from common.registry import EVENT_REGISTRY


class FakeFuture:
    def __init__(self, error=None):
        self.error = error

    def result(self):
        if self.error:
            raise self.error


class FakeAdmin:
    errors = {}  # topic -> exception raised by its future

    def __init__(self, config):
        self.config = config
        self.created = []
        FakeAdmin.last = self

    def create_topics(self, topics):
        self.created = topics
        return {t.topic: FakeFuture(self.errors.get(t.topic)) for t in topics}


class FakeRegistry:
    def __init__(self, config):
        self.config = config
        self.registered = []
        FakeRegistry.last = self

    def register_schema(self, subject, schema):
        self.registered.append((subject, schema))
        return len(self.registered)


@pytest.fixture
def kafka_bootstrap(app_module, monkeypatch):
    mod = app_module("bootstrap", "kafka")
    FakeAdmin.errors = {}
    monkeypatch.setattr(mod, "AdminClient", FakeAdmin)
    monkeypatch.setattr(mod, "SchemaRegistryClient", FakeRegistry)
    return mod


def test_creates_one_single_partition_topic_per_event(kafka_bootstrap):
    kafka_bootstrap.create_topics()

    created = {t.topic: t for t in FakeAdmin.last.created}
    assert set(created) == {cls.topic for cls in EVENT_REGISTRY.values()}
    assert all(t.num_partitions == 1 and t.replication_factor == 1 for t in created.values())


def test_existing_topics_are_not_an_error(kafka_bootstrap, capsys):
    FakeAdmin.errors = {"search-events": KafkaException(KafkaError(KafkaError.TOPIC_ALREADY_EXISTS))}

    kafka_bootstrap.create_topics()

    assert "Topic search-events already exists" in capsys.readouterr().out


def test_other_topic_errors_fail_the_bootstrap(kafka_bootstrap):
    FakeAdmin.errors = {"search-events": KafkaException(KafkaError(KafkaError._TIMED_OUT))}

    with pytest.raises(KafkaException):
        kafka_bootstrap.create_topics()


def test_registers_each_event_schema_under_its_topic_value_subject(kafka_bootstrap):
    kafka_bootstrap.register_schemas()

    registered = dict(FakeRegistry.last.registered)
    assert set(registered) == {f"{cls.topic}-value" for cls in EVENT_REGISTRY.values()}
    schema = registered["purchase-events-value"]
    assert schema.schema_type == "AVRO"
    assert json.loads(schema.schema_str)["name"] == "purchase"
