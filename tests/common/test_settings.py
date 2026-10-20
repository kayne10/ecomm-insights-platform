import importlib

import common.settings as settings


def test_defaults_target_the_compose_network(monkeypatch):
    for var in ("KAFKA_BOOTSTRAP_SERVERS", "SCHEMA_REGISTRY_URL", "ELASTICSEARCH_URL",
                "CONNECT_URL", "KIBANA_URL"):
        monkeypatch.delenv(var, raising=False)
    mod = importlib.reload(settings)

    assert mod.KafkaConfig.BOOTSTRAP_SERVERS == "kafka:9092"
    assert mod.SchemaRegistryConfig.URL == "http://schema-registry:8081"
    assert mod.ElasticsearchConfig.URL == "http://elasticsearch:9200"
    assert mod.ConnectConfig.URL == "http://connect:8083"
    assert mod.KibanaConfig.URL == "http://kibana:5601"


def test_environment_overrides_for_running_on_the_host(monkeypatch):
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
    monkeypatch.setenv("ELASTICSEARCH_URL", "http://localhost:9200")
    mod = importlib.reload(settings)

    assert mod.KafkaConfig.BOOTSTRAP_SERVERS == "localhost:29092"
    assert mod.ElasticsearchConfig.URL == "http://localhost:9200"

    monkeypatch.undo()
    importlib.reload(settings)  # restore defaults for other tests
