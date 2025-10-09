import requests
import logging
from common.registry import EVENT_REGISTRY

ES_HOST = "http://elasticsearch:9200"

logger = logging.getLogger(__name__)

def create_ilm_policy(event_name):
    policy_name = f"{event_name}_policy"
    url = f"{ES_HOST}/_ilm/policy/{policy_name}"
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

    r = requests.put(url, json=payload)
    r.raise_for_status()
    logger.info(f"✅ Created ILM policy: {policy_name}")

def create_index_template(event_name, mapping):
    template_name = f"{event_name}_template"
    policy_name = f"{event_name}_policy"
    index_pattern = f"{event_name}_*"
    url = f"{ES_HOST}/_index_template/{template_name}"
    payload = {
        "index_patterns": [index_pattern],
        "template": {
            "settings": {
                "index.lifecycle.name": policy_name,
                "index.lifecycle.rollover_alias": event_name
            },
            "mappings": mapping
        }
    }

    r = requests.put(url, json=payload)
    r.raise_for_status()
    logger.info(f"✅ Created index template: {template_name}")

def create_index_and_alias(event_name):
    index_name = f"{event_name}_v1"
    url = f"{ES_HOST}/{index_name}"
    payload = {"aliases": {event_name: {"is_write_index": True}}}

    r = requests.put(url, json=payload)
    r.raise_for_status()
    logger.info(f"✅ Created index: {index_name} with alias: {event_name}")

def bootstrap_elasticsearch():
    for event_name, event_cls in EVENT_REGISTRY.items():
        mapping = event_cls.to_es_mapping()
        create_ilm_policy(event_name)
        create_index_template(event_name, mapping)
        create_index_and_alias(event_name)

if __name__ == "__main__":
    bootstrap_elasticsearch()