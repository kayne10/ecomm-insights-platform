"""Create Elasticsearch ILM policies, index templates and write aliases. Safe to re-run."""
import logging

import requests
from common.registry import EVENT_REGISTRY
from common.settings import ElasticsearchConfig

ES_HOST = ElasticsearchConfig.URL

logging.basicConfig(level=logging.INFO, format="[Elasticsearch] %(message)s")
logger = logging.getLogger(__name__)


def create_ilm_policy(event_name):
    policy_name = f"{event_name}_policy"
    payload = {
        "policy": {
            "phases": {
                "hot": {
                    "actions": {
                        "rollover": {
                            "max_age": "7d",
                            "max_size": "50gb"
                        }
                    }
                },
                "delete": {
                    "min_age": "30d",
                    "actions": {"delete": {}}
                }
            }
        }
    }

    r = requests.put(f"{ES_HOST}/_ilm/policy/{policy_name}", json=payload)
    r.raise_for_status()
    logger.info(f"✅ ILM policy: {policy_name}")


def create_index_template(event_name, mapping):
    template_name = f"{event_name}_template"
    payload = {
        "index_patterns": [f"{event_name}_*"],
        "template": {
            "settings": {
                "index.lifecycle.name": f"{event_name}_policy",
                "index.lifecycle.rollover_alias": event_name,
                "number_of_shards": 1
            },
            "mappings": mapping
        }
    }

    r = requests.put(f"{ES_HOST}/_index_template/{template_name}", json=payload)
    r.raise_for_status()
    logger.info(f"✅ Index template: {template_name}")


def create_index_and_alias(event_name):
    # Skip if the write alias already exists (e.g. after a rollover or a previous bootstrap).
    if requests.head(f"{ES_HOST}/_alias/{event_name}").status_code == 200:
        logger.info(f"⏭️  Alias {event_name} already exists")
        return

    index_name = f"{event_name}_v1-000001"
    payload = {"aliases": {event_name: {"is_write_index": True}}}

    r = requests.put(f"{ES_HOST}/{index_name}", json=payload)
    r.raise_for_status()
    logger.info(f"✅ Index {index_name} with write alias {event_name}")


def bootstrap_elasticsearch():
    for event_name, event_cls in EVENT_REGISTRY.items():
        create_ilm_policy(event_name)
        create_index_template(event_name, event_cls.to_es_mapping())
        create_index_and_alias(event_name)


if __name__ == "__main__":
    bootstrap_elasticsearch()
