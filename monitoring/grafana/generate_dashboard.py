"""
Generates monitoring/grafana/dashboards/streaming-pipeline.json, the provisioned Grafana dashboard.

    make grafana-dashboard     # regenerate after editing this file; Grafana reloads within ~10 s

Edits made in the Grafana UI are not saved to the JSON file. To keep them, either port them
here or export the dashboard JSON from Grafana over the generated file.
"""
import json
import sys
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent / "dashboards" / "streaming-pipeline.json"

DS = {"type": "prometheus", "uid": "prometheus"}
EVENT_TOPICS = 'topic=~".+-events"'
PRODUCED_TOPICS = 'topic=~".+-events", topic!="cart-abandoned-events"'
EVENT_INDEX = 'index=~"[a-z][a-z_]*_v[0-9]+-[0-9]+"'
SINKS = 'consumergroup=~"connect-.+_es_sink"'
DETECTOR = 'operator_name="detect_abandoned_carts"'
SOURCE = 'operator_name=~"Source.*"'

panels = []
_next_id = [1]


def nid():
    _next_id[0] += 1
    return _next_id[0]


def target(expr, legend="", ref="A", instant=False):
    t = {"datasource": DS, "expr": expr, "legendFormat": legend, "refId": ref, "range": not instant}
    if instant:
        t["instant"] = True
    return t


def row(title, y):
    panels.append({"type": "row", "title": title, "id": nid(), "collapsed": False,
                   "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []})


def stat(title, expr, x, y, w=4, h=4, unit="short", thresholds=None, decimals=None,
         description="", no_value="0", mappings=None, color_mode="background"):
    steps = thresholds or [{"color": "green", "value": None}]
    defaults = {"unit": unit, "thresholds": {"mode": "absolute", "steps": steps},
                "color": {"mode": "thresholds"}, "noValue": no_value}
    if decimals is not None:
        defaults["decimals"] = decimals
    if mappings:
        defaults["mappings"] = mappings
    panels.append({
        "type": "stat", "title": title, "id": nid(), "description": description,
        "datasource": DS, "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [target(expr, instant=True)],
        "fieldConfig": {"defaults": defaults, "overrides": []},
        "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                    "colorMode": color_mode, "graphMode": "area", "justifyMode": "center",
                    "textMode": "value", "orientation": "auto", "wideLayout": True},
    })


def timeseries(title, targets, x, y, w, h=8, unit="short", stack=False, description="",
               fill=15, overrides=None, min_zero=True, legend="list"):
    custom = {"drawStyle": "line", "lineInterpolation": "smooth", "lineWidth": 2,
              "fillOpacity": fill, "gradientMode": "opacity", "showPoints": "never",
              "spanNulls": False, "stacking": {"mode": "normal" if stack else "none", "group": "A"},
              "axisSoftMin": 0 if min_zero else None}
    panels.append({
        "type": "timeseries", "title": title, "id": nid(), "description": description,
        "datasource": DS, "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": targets,
        "fieldConfig": {"defaults": {"unit": unit, "custom": custom,
                                     "color": {"mode": "palette-classic"}},
                        "overrides": overrides or []},
        "options": {"legend": {"displayMode": legend, "placement": "bottom", "showLegend": True,
                               "calcs": ["lastNotNull", "max"] if legend == "table" else []},
                    "tooltip": {"mode": "multi", "sort": "desc"}},
    })


def bargauge(title, expr, legend, x, y, w, h=8, unit="short", description=""):
    panels.append({
        "type": "bargauge", "title": title, "id": nid(), "description": description,
        "datasource": DS, "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [target(expr, legend, instant=True)],
        "fieldConfig": {"defaults": {"unit": unit, "color": {"mode": "continuous-BlPu"},
                                     "min": 0, "thresholds": {"mode": "absolute",
                                                              "steps": [{"color": "green", "value": None}]}},
                        "overrides": []},
        "options": {"orientation": "horizontal", "displayMode": "gradient", "showUnfilled": True,
                    "valueMode": "color", "namePlacement": "left", "sizing": "auto",
                    "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}},
    })


def color(name, c):
    return {"matcher": {"id": "byName", "options": name},
            "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": c}}]}


def short_sink(expr):
    """connect-refund_es_sink -> refund"""
    return f'label_replace({expr}, "sink", "$1", "consumergroup", "connect-(.+)_es_sink")'


def short_task(metric):
    """Source:_checkouts_and_purchases____with_cart_id -> source; detect_abandoned_carts____... -> detector"""
    return (f'max by (task) (label_replace(label_replace({metric}, "task", "source", "task_name", "Source.*"), '
            f'"task", "detector", "task_name", "detect.*")) / 1000')


def by_event(expr):
    """refund_v1-000001 -> refund"""
    return f'sum by (event) (label_replace({expr}, "event", "$1", "index", "(.+)_v[0-9]+-[0-9]+"))'


GREEN, YELLOW, ORANGE, RED, BLUE, PURPLE = "green", "yellow", "orange", "red", "blue", "purple"

# --- Row: overview ------------------------------------------------------------------
row("Pipeline overview", 0)
stat("Events in / s", f"sum(rate(kafka_topic_partition_current_offset{{{PRODUCED_TOPICS}}}[1m]))",
     0, 1, unit="suffix: ev/s", decimals=1,
     thresholds=[{"color": "text", "value": None}, {"color": BLUE, "value": 0.01}],
     description="Events produced to Kafka per second, across all generated event topics.")
stat("Docs indexed / s", f"sum(rate(elasticsearch_index_stats_indexing_index_total{{{EVENT_INDEX}}}[1m]))",
     4, 1, unit="suffix: docs/s", decimals=1,
     thresholds=[{"color": "text", "value": None}, {"color": GREEN, "value": 0.01}],
     description="Documents written to the event indices per second by the Elasticsearch sinks.")
stat("Sink lag", f"sum(kafka_consumergroup_lag{{{SINKS}}})", 8, 1, unit="short",
     thresholds=[{"color": GREEN, "value": None}, {"color": YELLOW, "value": 100}, {"color": RED, "value": 1000}],
     description="Messages in Kafka not yet written to Elasticsearch, summed over all sinks. "
                 "Connect commits offsets every 10 s, so small numbers are normal.")
stat("Flink job uptime", "max(flink_jobmanager_job_uptime)", 12, 1, unit="dtdurationms",
     no_value="not running", thresholds=[{"color": GREEN, "value": None}],
     description="Uptime of the cart abandonment job. 'not running' means the flink profile is down.")
stat("Carts abandoned", "sum(increase(flink_taskmanager_job_task_operator_cartsAbandoned[$__range]))",
     16, 1, decimals=0, thresholds=[{"color": PURPLE, "value": None}],
     description="Abandoned carts detected by Flink in the selected time range.")
stat("Abandonment rate",
     "sum(increase(flink_taskmanager_job_task_operator_cartsAbandoned[$__range])) / "
     "(sum(increase(flink_taskmanager_job_task_operator_cartsAbandoned[$__range])) + "
     "sum(increase(flink_taskmanager_job_task_operator_cartsConverted[$__range])))",
     20, 1, unit="percentunit", decimals=1, no_value="–",
     thresholds=[{"color": GREEN, "value": None}, {"color": YELLOW, "value": 0.3}, {"color": RED, "value": 0.6}],
     description="Abandoned / (abandoned + converted) carts in the selected range, as decided by Flink.")

health_mappings = [{"type": "value", "options": {
    "2": {"text": "green", "color": GREEN}, "1": {"text": "yellow (1 node)", "color": YELLOW},
    "0": {"text": "red", "color": RED}}}]
stat("Scrape targets up", "sum(up) / count(up)", 0, 5, unit="percentunit", decimals=0,
     thresholds=[{"color": RED, "value": None}, {"color": YELLOW, "value": 0.6}, {"color": GREEN, "value": 0.99}],
     description="Share of Prometheus targets reachable. Flink targets are down when its profile isn't running.",
     color_mode="value")
stat("Kafka brokers", "max(kafka_brokers)", 4, 5, decimals=0,
     thresholds=[{"color": RED, "value": None}, {"color": GREEN, "value": 1}], color_mode="value")
stat("Elasticsearch health",
     'max(elasticsearch_cluster_health_status{color="green"}) * 2 + max(elasticsearch_cluster_health_status{color="yellow"})',
     8, 5, mappings=health_mappings, color_mode="value",
     description="Yellow is expected locally: a single node can't host replica shards.")
stat("Documents in event indices", f"sum(elasticsearch_indices_docs_primary{{{EVENT_INDEX}}})", 12, 5,
     decimals=0, color_mode="value", thresholds=[{"color": "text", "value": None}])
stat("Flink restarts", "max(flink_jobmanager_job_numRestarts)", 16, 5, decimals=0, no_value="–",
     thresholds=[{"color": GREEN, "value": None}, {"color": RED, "value": 1}], color_mode="value")
stat("Failed checkpoints", "max(flink_jobmanager_job_numberOfFailedCheckpoints)", 20, 5, decimals=0,
     no_value="–", thresholds=[{"color": GREEN, "value": None}, {"color": RED, "value": 1}], color_mode="value")

# --- Row: Kafka ---------------------------------------------------------------------
row("Kafka throughput", 9)
timeseries("Events per second by topic",
           [target(f"sum by (topic) (rate(kafka_topic_partition_current_offset{{{EVENT_TOPICS}}}[1m]))", "{{topic}}")],
           0, 10, 16, unit="suffix: ev/s", stack=True, fill=35,
           description="Produce rate per topic, from the growth of each partition's latest offset.")
bargauge("Messages per topic", f"sort_desc(sum by (topic) (kafka_topic_partition_current_offset{{{EVENT_TOPICS}}}))",
         "{{topic}}", 16, 10, 8,
         description="Total messages written to each topic since it was created.")

# --- Row: sinks / Elasticsearch -------------------------------------------------------
row("Kafka Connect → Elasticsearch", 18)
timeseries("Kafka in vs Elasticsearch out",
           [target(f"sum(rate(kafka_topic_partition_current_offset{{{EVENT_TOPICS}}}[1m]))", "Kafka in", "A"),
            target(f"sum(rate(elasticsearch_index_stats_indexing_index_total{{{EVENT_INDEX}}}[1m]))",
                   "Elasticsearch out", "B")],
           0, 19, 12, unit="suffix: /s", fill=10,
           overrides=[color("Kafka in", BLUE), color("Elasticsearch out", GREEN)],
           description="When the two lines track each other the sinks keep up. A gap that keeps growing means the sinks fall behind.")
timeseries("Consumer lag by sink",
           [target(short_sink(f"sum by (consumergroup) (kafka_consumergroup_lag{{{SINKS}}})"), "{{sink}}")],
           12, 19, 12, unit="short", fill=5,
           description="Messages waiting per Elasticsearch sink. Should bounce back to ~0 every offset commit (10 s).")
timeseries("Documents indexed per second by event",
           [target(by_event(f"sum by (index) (rate(elasticsearch_index_stats_indexing_index_total{{{EVENT_INDEX}}}[1m]))"),
                   "{{event}}")],
           0, 27, 12, unit="suffix: docs/s", stack=True, fill=35)
timeseries("Elasticsearch indexing latency and heap",
           [target("sum(rate(elasticsearch_indices_indexing_index_time_seconds_total[1m])) / "
                   "sum(rate(elasticsearch_indices_indexing_index_total[1m]))", "avg time per doc", "A"),
            target('max(elasticsearch_jvm_memory_used_bytes{area="heap"}) / max(elasticsearch_jvm_memory_max_bytes{area="heap"})',
                   "JVM heap used", "B")],
           12, 27, 12, unit="s", fill=5,
           overrides=[{"matcher": {"id": "byName", "options": "JVM heap used"},
                       "properties": [{"id": "unit", "value": "percentunit"},
                                      {"id": "custom.axisPlacement", "value": "right"},
                                      {"id": "max", "value": 1},
                                      {"id": "color", "value": {"mode": "fixed", "fixedColor": ORANGE}}]}])

# --- Row: Flink ---------------------------------------------------------------------
row("Flink: cart abandonment job", 35)
timeseries("Carts converted vs abandoned (per minute)",
           [target("sum(rate(flink_taskmanager_job_task_operator_cartsConverted[1m])) * 60", "converted", "A"),
            target("sum(rate(flink_taskmanager_job_task_operator_cartsAbandoned[1m])) * 60", "abandoned", "B")],
           0, 36, 8, unit="short", fill=20,
           overrides=[color("converted", GREEN), color("abandoned", PURPLE)],
           description="Decisions made by the detector. Abandonments trail checkouts by the 2 minute timeout.")
timeseries("Records per second through the job",
           [target(f"sum(flink_taskmanager_job_task_operator_numRecordsOutPerSecond{{{SOURCE}}})", "source: checkouts + purchases", "A"),
            target(f"sum(flink_taskmanager_job_task_operator_numRecordsInPerSecond{{{DETECTOR}}})", "detector in (with cart_id)", "B"),
            target(f"sum(flink_taskmanager_job_task_operator_numRecordsOutPerSecond{{{DETECTOR}}})", "abandoned carts out", "C")],
           8, 36, 8, unit="suffix: rec/s", fill=5)
timeseries("Event-time lag",
           [target(f"max(flink_taskmanager_job_task_operator_currentEmitEventTimeLag{{{SOURCE}}})", "source emit lag", "A"),
            # Before the first watermark Flink reports Long.MIN_VALUE; ignore it instead of plotting ~300M years.
            target(f"time() * 1000 - (max(flink_taskmanager_job_task_operator_currentInputWatermark{{{DETECTOR}}}) > 0)",
                   "detector watermark lag", "B")],
           16, 36, 8, unit="ms", fill=5,
           description="How far event time trails the wall clock. The watermark lag grows while no events arrive; "
                       "abandonment timers only fire once the watermark passes them.")
timeseries("Busy and backpressured time",
           [target(short_task("flink_taskmanager_job_task_busyTimeMsPerSecond"), "busy: {{task}}", "A"),
            target(short_task("flink_taskmanager_job_task_backPressuredTimeMsPerSecond"), "backpressured: {{task}}", "B")],
           0, 44, 8, unit="percentunit", fill=5,
           description="Share of each second a task is busy or blocked by downstream. Sustained backpressure means the sink or detector can't keep up.")
timeseries("Checkpoints",
           [target("max(flink_jobmanager_job_lastCheckpointDuration)", "last duration", "A"),
            target("max(flink_jobmanager_job_lastCheckpointSize)", "last size", "B")],
           8, 44, 8, unit="ms", fill=5,
           overrides=[{"matcher": {"id": "byName", "options": "last size"},
                       "properties": [{"id": "unit", "value": "bytes"},
                                      {"id": "custom.axisPlacement", "value": "right"}]}],
           description="Checkpoints every 30 s store detector state (pending carts) and commit Kafka offsets.")
timeseries("Flink source lag and JVM heap",
           [target("max(flink_taskmanager_job_task_operator_KafkaSourceReader_KafkaConsumer_records_lag_max)",
                   "Kafka records behind", "A"),
            target("max(flink_taskmanager_Status_JVM_Memory_Heap_Used)", "TaskManager heap", "B"),
            target("max(flink_jobmanager_Status_JVM_Memory_Heap_Used)", "JobManager heap", "C")],
           16, 44, 8, unit="short", fill=5,
           overrides=[{"matcher": {"id": "byRegexp", "options": ".*heap"},
                       "properties": [{"id": "unit", "value": "bytes"},
                                      {"id": "custom.axisPlacement", "value": "right"}]}])

dashboard = {
    "uid": "streaming-pipeline",
    "title": "Streaming Pipeline",
    "description": "Throughput, lag and health of Kafka, the Elasticsearch sinks and the Flink job. "
                   "Provisioned from monitoring/grafana/dashboards/streaming-pipeline.json.",
    "tags": ["ecomm", "kafka", "flink", "elasticsearch"],
    "timezone": "browser",
    "editable": True,
    "graphTooltip": 1,
    "refresh": "5s",
    "time": {"from": "now-15m", "to": "now"},
    "timepicker": {"refresh_intervals": ["5s", "10s", "30s", "1m", "5m"]},
    "schemaVersion": 41,
    "version": 1,
    "links": [
        {"title": "Kibana insights", "type": "link", "icon": "external link", "targetBlank": True,
         "url": "http://localhost:5601/app/dashboards#/view/ecomm-insights"},
        {"title": "Flink UI", "type": "link", "icon": "external link", "targetBlank": True,
         "url": "http://localhost:8082"},
        {"title": "Prometheus targets", "type": "link", "icon": "external link", "targetBlank": True,
         "url": "http://localhost:9090/targets"},
    ],
    "templating": {"list": []},
    "annotations": {"list": [{"builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"},
                              "enable": True, "hide": True, "iconColor": "rgba(0, 211, 255, 1)",
                              "name": "Annotations & Alerts", "type": "dashboard"}]},
    "panels": panels,
}

out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT
with open(out, "w") as f:
    json.dump(dashboard, f, indent=2)
    f.write("\n")
print(f"{len([p for p in panels if p['type'] != 'row'])} panels written to {out}")
