import pytest

from common.registry import EVENT_REGISTRY


@pytest.fixture
def connect(app_module, monkeypatch, fake_http):
    mod = app_module("bootstrap", "connect")
    http = fake_http()
    monkeypatch.setattr(mod, "requests", http)
    mod.http = http
    return mod


def test_connector_is_named_after_the_event(connect):
    assert connect.connector_name("refund") == "refund_es_sink"


def test_sink_writes_the_topic_into_the_event_alias(connect):
    config = connect.sink_config(EVENT_REGISTRY["refund"])

    assert config["topics"] == "refund-events"
    assert config["external.resource.usage"] == "ALIAS_INDEX"
    assert config["topic.to.external.resource.mapping"] == "refund-events:refund"


def test_sink_uses_the_event_id_key_as_document_id(connect):
    config = connect.sink_config(EVENT_REGISTRY["refund"])

    # key.ignore=false -> _id is the Kafka key (event_id), so replays overwrite, not duplicate
    assert config["key.ignore"] == "false"
    assert config["schema.ignore"] == "true"
    assert config["value.converter"] == "io.confluent.connect.avro.AvroConverter"


def test_applies_one_sink_per_registered_event(connect, capsys, fake_response):
    connect.http.routes = [("PUT", "/connectors/refund_es_sink", fake_response(201))]

    assert connect.apply_sinks() is True

    urls = [c["url"] for c in connect.http.calls]
    assert len(urls) == len(EVENT_REGISTRY)
    assert all(u.endswith("/config") for u in urls)
    out = capsys.readouterr().out
    assert "Created refund_es_sink" in out
    assert "Updated search_es_sink" in out


def test_can_limit_to_some_events(connect):
    connect.apply_sinks({"refund", "search"})

    assert {c["json"]["topics"] for c in connect.http.calls} == {"refund-events", "search-events"}


def test_reports_failure_when_connect_rejects_a_config(connect, fake_response):
    connect.http.routes = [("PUT", "/connectors/refund_es_sink", fake_response(400, text="bad"))]

    assert connect.apply_sinks() is False
