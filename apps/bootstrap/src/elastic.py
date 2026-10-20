"""
Create Elasticsearch resources for every registered event. Safe to re-run.

Per event:
  * ILM policy           <event>_policy
  * index template       <event>_template   (mapping, ILM, ingest pipeline, search aliases)
  * first index          <event>_v1-000001  with write alias <event>

Shared:
  * ingest pipeline      events-enrich      fills a common @timestamp on every document
  * search aliases       events             every event type
                         events-<domain>    e.g. events-orders = purchase + refund

Existing indices are brought up to date in place (additive mapping changes, settings,
aliases) and documents missing @timestamp are backfilled, so no `make reset` is needed.
"""
import logging
from collections import defaultdict

import requests
from common.registry import EVENT_REGISTRY
from common.settings import ElasticsearchConfig

ES_HOST = ElasticsearchConfig.URL
PIPELINE = "events-enrich"
ALL_EVENTS_ALIAS = "events"

logging.basicConfig(level=logging.INFO, format="[Elasticsearch] %(message)s")
logger = logging.getLogger(__name__)


def es(method, path, **kwargs):
    r = requests.request(method, f"{ES_HOST}{path}", **kwargs)
    if not r.ok:
        raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text}")
    return r


def search_aliases(event_cls):
    return [ALL_EVENTS_ALIAS, f"{ALL_EVENTS_ALIAS}-{event_cls.domain}"]


def create_ingest_pipeline():
    """
    Original events name their time field differently (timestamp / viewed_at / searched_at)
    and some store it as keyword. Copy whichever exists into a real `@timestamp` date,
    falling back to ingest time.
    """
    payload = {
        "description": "Normalize event time into @timestamp",
        "processors": [
            {"set": {"field": "@timestamp", "copy_from": source, "override": False,
                     "if": f"ctx['@timestamp'] == null && ctx.{source} != null"}}
            for source in ("timestamp", "viewed_at", "searched_at")
        ] + [
            {"set": {"field": "@timestamp", "value": "{{{_ingest.timestamp}}}", "override": False}},
        ],
    }
    es("PUT", f"/_ingest/pipeline/{PIPELINE}", json=payload)
    logger.info(f"✅ Ingest pipeline: {PIPELINE}")


def create_ilm_policy(event_name):
    policy_name = f"{event_name}_policy"
    payload = {
        "policy": {
            "phases": {
                "hot": {"actions": {"rollover": {"max_age": "7d", "max_size": "50gb"}}},
                "delete": {"min_age": "30d", "actions": {"delete": {}}},
            }
        }
    }
    es("PUT", f"/_ilm/policy/{policy_name}", json=payload)
    logger.info(f"✅ ILM policy: {policy_name}")


def create_index_template(event_name, event_cls):
    template_name = f"{event_name}_template"
    payload = {
        "index_patterns": [f"{event_name}_*"],
        "template": {
            "settings": {
                "index.lifecycle.name": f"{event_name}_policy",
                "index.lifecycle.rollover_alias": event_name,
                "index.default_pipeline": PIPELINE,
                "number_of_shards": 1,
            },
            "mappings": event_cls.to_es_mapping(),
            # Read-only search aliases; rolled-over indices join them automatically.
            "aliases": {alias: {} for alias in search_aliases(event_cls)},
        },
    }
    es("PUT", f"/_index_template/{template_name}", json=payload)
    logger.info(f"✅ Index template: {template_name}")


def create_index_and_alias(event_name):
    # Skip if the write alias already exists (e.g. after a rollover or a previous bootstrap).
    if requests.head(f"{ES_HOST}/_alias/{event_name}").status_code == 200:
        logger.info(f"⏭️  Alias {event_name} already exists")
        return

    index_name = f"{event_name}_v1-000001"
    es("PUT", f"/{index_name}", json={"aliases": {event_name: {"is_write_index": True}}})
    logger.info(f"✅ Index {index_name} with write alias {event_name}")


def sync_existing_indices(event_name, event_cls):
    """Apply template changes to indices created before them. Only additive mapping changes."""
    pattern = f"{event_name}_*"
    es("PUT", f"/{pattern}/_mapping", json=event_cls.to_es_mapping())
    es("PUT", f"/{pattern}/_settings", json={"index.default_pipeline": PIPELINE})
    actions = [{"add": {"index": pattern, "alias": alias}} for alias in search_aliases(event_cls)]
    es("POST", "/_aliases", json={"actions": actions})


def backfill_timestamps():
    """Run the pipeline over documents indexed before it existed."""
    r = es(
        "POST",
        f"/{ALL_EVENTS_ALIAS}/_update_by_query",
        params={"pipeline": PIPELINE, "conflicts": "proceed", "refresh": "true"},
        json={"query": {"bool": {"must_not": {"exists": {"field": "@timestamp"}}}}},
        timeout=300,
    )
    updated = r.json().get("updated", 0)
    if updated:
        logger.info(f"✅ Backfilled @timestamp on {updated} existing documents")


def bootstrap_elasticsearch():
    create_ingest_pipeline()
    domains = defaultdict(list)
    for event_name, event_cls in EVENT_REGISTRY.items():
        create_ilm_policy(event_name)
        create_index_template(event_name, event_cls)
        create_index_and_alias(event_name)
        sync_existing_indices(event_name, event_cls)
        domains[event_cls.domain].append(event_name)

    backfill_timestamps()
    logger.info(f"🔎 Search alias {ALL_EVENTS_ALIAS}: all {len(EVENT_REGISTRY)} event types")
    for domain, names in sorted(domains.items()):
        logger.info(f"🔎 Search alias {ALL_EVENTS_ALIAS}-{domain}: {', '.join(names)}")


if __name__ == "__main__":
    bootstrap_elasticsearch()
