import pytest

from common.registry import EVENT_REGISTRY


@pytest.fixture
def elastic(app_module, monkeypatch, fake_http):
    mod = app_module("bootstrap", "elastic")
    http = fake_http()
    monkeypatch.setattr(mod, "requests", http)
    mod.http = http
    return mod


def test_pipeline_copies_whichever_time_field_exists_then_falls_back_to_ingest_time(elastic):
    elastic.create_ingest_pipeline()

    (call,) = elastic.http.find("PUT", "/_ingest/pipeline/events-enrich")
    processors = [p["set"] for p in call["json"]["processors"]]
    assert [p.get("copy_from") for p in processors[:3]] == ["timestamp", "viewed_at", "searched_at"]
    assert all(p["field"] == "@timestamp" and p["override"] is False for p in processors)
    assert processors[-1]["value"] == "{{{_ingest.timestamp}}}"


def test_template_wires_ilm_pipeline_mapping_and_search_aliases(elastic):
    refund = EVENT_REGISTRY["refund"]
    elastic.create_index_template("refund", refund)

    (call,) = elastic.http.find("PUT", "/_index_template/refund_template")
    body = call["json"]
    settings = body["template"]["settings"]
    assert body["index_patterns"] == ["refund_*"]
    assert settings["index.lifecycle.name"] == "refund_policy"
    assert settings["index.lifecycle.rollover_alias"] == "refund"
    assert settings["index.default_pipeline"] == "events-enrich"
    assert body["template"]["mappings"] == refund.to_es_mapping()
    assert set(body["template"]["aliases"]) == {"events", "events-orders"}


def test_first_index_is_created_with_the_write_alias(elastic, fake_response):
    elastic.http.routes = [("HEAD", "/_alias/refund", fake_response(404))]

    elastic.create_index_and_alias("refund")

    (call,) = elastic.http.find("PUT", "/refund_v1-000001")
    assert call["json"] == {"aliases": {"refund": {"is_write_index": True}}}


def test_existing_write_alias_is_left_alone(elastic, fake_response):
    elastic.http.routes = [("HEAD", "/_alias/refund", fake_response(200))]

    elastic.create_index_and_alias("refund")

    assert elastic.http.find("PUT", "/refund_v1") == []


def test_existing_indices_get_mapping_pipeline_and_aliases(elastic):
    elastic.sync_existing_indices("search", EVENT_REGISTRY["search"])

    assert elastic.http.find("PUT", "/search_*/_mapping")
    (settings,) = elastic.http.find("PUT", "/search_*/_settings")
    assert settings["json"] == {"index.default_pipeline": "events-enrich"}
    (aliases,) = elastic.http.find("POST", "/_aliases")
    added = {a["add"]["alias"] for a in aliases["json"]["actions"]}
    assert added == {"events", "events-browsing"}


def test_backfill_only_touches_documents_without_timestamp(elastic, fake_response):
    elastic.http.routes = [("POST", "_update_by_query", fake_response(200, {"updated": 3}))]

    elastic.backfill_timestamps()

    (call,) = elastic.http.find("POST", "/events/_update_by_query")
    assert call["params"]["pipeline"] == "events-enrich"
    assert call["json"]["query"] == {"bool": {"must_not": {"exists": {"field": "@timestamp"}}}}


def test_errors_from_elasticsearch_are_raised_with_context(elastic, fake_response):
    elastic.http.routes = [("PUT", "/_ilm/policy/", fake_response(400, text="bad policy"))]

    with pytest.raises(RuntimeError, match="400: bad policy"):
        elastic.create_ilm_policy("refund")


def test_full_bootstrap_covers_every_event(elastic, fake_response):
    elastic.http.routes = [("HEAD", "/_alias/", fake_response(404))]

    elastic.bootstrap_elasticsearch()

    for name in EVENT_REGISTRY:
        assert elastic.http.find("PUT", f"/_ilm/policy/{name}_policy")
        assert elastic.http.find("PUT", f"/_index_template/{name}_template")
        assert elastic.http.find("PUT", f"/{name}_v1-000001")
