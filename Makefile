# One entry point for local development. Run `make` to see all targets.
.DEFAULT_GOAL := help
SHELL := /bin/bash

EVENTS   ?= add_to_cart
COUNT    ?= 20
INTERVAL ?= 0.5
SVC      ?=
ES       ?= http://localhost:9200
TOPIC    ?= add-to-cart-events
MAX      ?= 10
GROUP    ?= connect-add_to_cart_es_sink
SINK     ?= add_to_cart
EVERY    ?= 2

# kafkactl always uses the repo config + context, independent of your global ~/.config/kafkactl
KAFKACTL := kafkactl -C kafkactl.yml --context ecomm-local

.PHONY: help up down restart reset ps logs build bootstrap sink produce stream dev \
        connectors sink-status es-count es-indices topics subjects tail urls \
        kctl-check kctl-topics kctl-topic kctl-groups kctl-group kctl-lag kctl-watch kctl-consume kctl-follow \
        es-watch es-search dashboards observe observe-kill connect-errors stats docker-ui sink-lag sink-lag-watch

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage: make <target> [VAR=value]\n\n"} \
	  /^[a-zA-Z_-]+:.*##/ { printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@printf "\nVariables: EVENTS=$(EVENTS) COUNT=$(COUNT) INTERVAL=$(INTERVAL) TOPIC=$(TOPIC) MAX=$(MAX) GROUP=$(GROUP) SINK=$(SINK) EVERY=$(EVERY) SVC=<service>\n\n"

## --- Lifecycle -------------------------------------------------------------
up: ## Start infra and wait until every service is healthy
	docker compose up -d --wait
	@$(MAKE) --no-print-directory urls

down: ## Stop the stack (keeps data volumes)
	docker compose down

restart: ## Restart one service: make restart SVC=connect
	docker compose restart $(SVC)

reset: ## Destroy containers AND volumes (fresh Kafka + ES), then bring infra back up
	docker compose down -v --remove-orphans
	@$(MAKE) --no-print-directory up

build: ## Rebuild the bootstrap/producer images (after requirements.txt changes)
	docker compose --profile tools build

ps: ## Show service status and health
	docker compose ps -a

logs: ## Tail logs: make logs SVC=connect (all services if SVC unset)
	docker compose logs -f --tail=100 $(SVC)

urls: ## Print local endpoints
	@echo ""
	@echo "  Kafka (host)       localhost:29092"
	@echo "  Schema Registry    http://localhost:8081"
	@echo "  Kafka Connect      http://localhost:8083"
	@echo "  Elasticsearch      http://localhost:9200"
	@echo "  Kibana             http://localhost:5601"
	@echo "  Dashboard          http://localhost:5601/app/dashboards#/view/ecomm-insights"
	@echo ""

## --- Pipeline --------------------------------------------------------------
bootstrap: ## Create topics, schemas, ES policies/templates/aliases (idempotent)
	docker compose run --rm bootstrap

sink: ## Create/update an ES sink for every event, plus hand-written connectors
	@bin/kc wait
	docker compose run --rm bootstrap python connect.py
	@bin/kc apply-all

produce: ## Send COUNT events: make produce EVENTS=add_to_cart,search COUNT=50
	bin/stream start $(EVENTS) $(COUNT) $(INTERVAL)

stream: ## Stream EVENTS forever (Ctrl-C to stop)
	bin/stream start $(EVENTS) 0 $(INTERVAL)

dev: up bootstrap sink dashboards ## Full setup: infra, topics, ES, sinks and Kibana dashboard
	@echo "✅ Ready. Try: make observe, then open the Kibana dashboard above"

dashboards: ## Create/overwrite Kibana data views and the Ecomm Insights dashboard
	docker compose run --rm bootstrap python kibana.py

## --- Inspect ---------------------------------------------------------------
connectors: ## List connectors and their state
	@bin/kc list

sink-status: ## Status with stack traces for one sink: make sink-status SINK=refund
	@bin/kc status $(SINK)

topics: ## List Kafka topics
	@docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

subjects: ## List Schema Registry subjects
	@curl -s http://localhost:8081/subjects | jq .

tail: ## Print MAX decoded Avro messages: make tail TOPIC=search-events MAX=5
	@docker compose exec -T schema-registry kafka-avro-console-consumer \
	  --bootstrap-server kafka:9092 --topic $(TOPIC) --from-beginning --max-messages $(MAX) \
	  --property schema.registry.url=http://localhost:8081 2>&1 | grep --line-buffered '^{' 

es-indices: ## List Elasticsearch indices and aliases
	@curl -s "$(ES)/_cat/indices?v&s=index" | grep -v '^.*\s\.'
	@echo ""
	@curl -s "$(ES)/_cat/aliases?v" | grep -v '\s\.'

es-count: ## Document count per event alias in Elasticsearch (every alias, auto-discovered)
	@for a in $$(curl -s "$(ES)/_cat/aliases?h=alias" | grep -v '^\.' | sort -u); do \
	  printf "  %-18s %s\n" $$a "$$(curl -s $(ES)/$$a/_count | jq -r '.count // .error.type')"; \
	done

Q ?= *
es-search: ## Search ALL event types: make es-search Q='reason:damaged OR rating:1' [SIZE=5]
	@curl -s -G "$(ES)/events/_search" --data-urlencode "q=$(Q)" \
	  --data-urlencode "size=$(or $(SIZE),5)" --data-urlencode "sort=@timestamp:desc" \
	  | jq -c '"\(.hits.total.value) hits", (.hits.hits[] | {index: ._index} + (._source | del(.event_id)))'

es-watch: ## Refresh ES doc counts every EVERY seconds (Ctrl-C to stop)
	@command -v watch >/dev/null || { echo "watch not found: brew install watch" >&2; exit 1; }
	@watch -t -n $(EVERY) 'echo "Elasticsearch doc counts (every $(EVERY)s)"; echo; $(MAKE) -s es-count'

## --- Monitoring with kafkactl (brew install kafkactl) -----------------------
kctl-check:
	@command -v kafkactl >/dev/null || { echo "kafkactl not found: brew install deviceinsight/packages/kafkactl" >&2; exit 1; }

kctl-topics: kctl-check ## Topics with partitions and configs
	@$(KAFKACTL) get topics -o wide

kctl-topic: kctl-check ## Partitions and offsets of one topic: make kctl-topic TOPIC=search-events
	@$(KAFKACTL) describe topic $(TOPIC)

kctl-groups: kctl-check ## Consumer groups and the topics they read
	@$(KAFKACTL) get consumer-groups -o wide

kctl-group: kctl-check ## Offsets, lag and members of one group: make kctl-group GROUP=<name>
	@$(KAFKACTL) describe consumer-group $(GROUP)

kctl-lag: kctl-check ## Lag per partition for every consumer group
	@for g in $$($(KAFKACTL) get consumer-groups -o wide | awk 'NR>1 && $$2=="consumer" {print $$1}'); do \
	  printf "\n\033[1m%s\033[0m\n" "$$g"; \
	  $(KAFKACTL) describe consumer-group "$$g" --print-members=false; \
	done

kctl-watch: kctl-check ## Refresh a group's lag every EVERY seconds (Ctrl-C to stop)
	@while true; do \
	  clear; echo "$(GROUP)  ($$(date +%T), every $(EVERY)s, Ctrl-C to stop)"; echo; \
	  $(KAFKACTL) describe consumer-group $(GROUP); \
	  sleep $(EVERY); \
	done

sink-lag: kctl-check ## Lag of every ES sink in one compact table
	@{ echo "SINK NEWEST COMMITTED LAG"; \
	  for g in $$($(KAFKACTL) get consumer-groups -o compact | grep -E '^connect-.*_es_sink$$' | sort); do \
	    $(KAFKACTL) describe consumer-group $$g --print-members=false \
	      | awk -v n="$${g#connect-}" 'NR>1 && NF>=7 {nw+=$$3; c+=$$5; l+=$$7} END {sub(/_es_sink$$/, "", n); print n, nw+0, c+0, l+0}'; \
	  done; } | column -t

sink-lag-watch: kctl-check ## Refresh the sink lag table every EVERY seconds
	@watch -t -n $(EVERY) 'echo "ES sink lag (every $(EVERY)s)"; echo; $(MAKE) -s sink-lag'

kctl-consume: kctl-check ## Print the last MAX decoded messages: make kctl-consume TOPIC=purchase-events
	@$(KAFKACTL) consume $(TOPIC) --tail $(MAX) --print-keys --print-timestamps

kctl-follow: kctl-check ## Stream new decoded messages as they arrive (Ctrl-C to stop)
	@$(KAFKACTL) consume $(TOPIC) --print-keys --print-timestamps

## --- Observe the whole pipeline (tmux, watch, lazydocker) -------------------
observe: ## tmux dashboard of every stage, streaming all events (override: EVENTS=search)
	@bin/observe $(if $(filter command line environment,$(origin EVENTS)),--events $(EVENTS)) \
	  --interval $(INTERVAL) --topic $(TOPIC) --every $(EVERY)

observe-kill: ## Close the observe tmux session (stops its producer)
	@bin/observe kill

connect-errors: ## Follow Kafka Connect logs, ERROR/WARN lines only
	@echo "Following kafka-connect ERROR/WARN lines. Empty means healthy."
	@docker compose logs -f --tail=200 connect 2>&1 | grep --line-buffered -E ' (ERROR|WARN) ' \
	  | grep --line-buffered -vE 'ServiceLoader manifests|StatusLogger Reconfiguration failed'

stats: ## Live CPU and memory per container
	@docker stats --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}'

docker-ui: ## Open lazydocker for this compose project
	@command -v lazydocker >/dev/null || { echo "lazydocker not found: brew install lazydocker" >&2; exit 1; }
	@lazydocker
