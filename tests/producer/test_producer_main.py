import pytest

from common.registry import EVENT_REGISTRY, GENERATED_EVENTS


class FakeProducer:
    def __init__(self, config):
        self.config = config
        self.produced = []
        self.flushes = 0
        FakeProducer.last = self

    def produce(self, topic, key, value, callback):
        self.produced.append({"topic": topic, "key": key, "value": value})

    def poll(self, timeout):
        return 0

    def flush(self):
        self.flushes += 1


@pytest.fixture
def producer_main(app_module, monkeypatch):
    mod = app_module("producer", "main")
    monkeypatch.setattr(mod, "Producer", FakeProducer)
    monkeypatch.setattr(mod, "SchemaRegistryClient", lambda config: object())
    # The real serializer talks to Schema Registry; pass the payload through instead.
    monkeypatch.setattr(mod, "AvroSerializer", lambda registry, schema, to_dict: (lambda payload, ctx: payload))
    return mod


def test_all_means_every_generated_event(producer_main):
    assert producer_main.resolve_events("all") == list(GENERATED_EVENTS.values())


def test_comma_list_with_spaces(producer_main):
    selected = producer_main.resolve_events(" search, refund ,")
    assert selected == [EVENT_REGISTRY["search"], EVENT_REGISTRY["refund"]]


def test_unknown_event_is_rejected_with_the_choices(producer_main):
    with pytest.raises(ValueError, match="Unknown event type: nope.*product_view"):
        producer_main.resolve_events("search,nope")


def test_derived_event_is_rejected(producer_main):
    with pytest.raises(ValueError, match="cart_abandoned is produced by flink"):
        producer_main.resolve_events("cart_abandoned")


def test_empty_selection_is_rejected(producer_main):
    with pytest.raises(ValueError):
        producer_main.resolve_events(" , ")


def test_list_shows_weights_and_derived_sources(producer_main):
    lines = producer_main.describe_events()
    assert len(lines) == len(EVENT_REGISTRY)
    assert any(line.startswith("refund") and "weight=0.2" in line for line in lines)
    assert any(line.startswith("cart_abandoned") and "produced by flink" in line for line in lines)


def test_stream_sends_limit_events_keyed_by_event_id(producer_main):
    search = EVENT_REGISTRY["search"]

    producer_main.stream([search], producer_main.ProducerConfig(), interval=0, limit=25)

    produced = FakeProducer.last.produced
    assert len(produced) == 25
    assert all(p["topic"] == "search-events" for p in produced)
    assert all(p["key"] == p["value"]["event_id"] for p in produced)
    # flushed every 10 events, and once more on the way out
    assert FakeProducer.last.flushes == 3


def test_stream_mix_follows_the_weights(producer_main):
    views, refunds = EVENT_REGISTRY["product_view"], EVENT_REGISTRY["refund"]

    producer_main.stream([views, refunds], producer_main.ProducerConfig(), interval=0, limit=1000)

    topics = [p["topic"] for p in FakeProducer.last.produced]
    # weights 10 : 0.2 -> about 2% refunds
    assert 0.005 < topics.count("refund-events") / len(topics) < 0.05


def test_producer_connects_to_the_shared_kafka_setting(producer_main):
    from common.settings import KafkaConfig

    assert producer_main.ProducerConfig.as_dict() == {"bootstrap.servers": KafkaConfig.BOOTSTRAP_SERVERS}
