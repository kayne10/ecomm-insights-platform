"""Static checks of the provisioned Grafana dashboard and Prometheus config (no Grafana needed)."""
import itertools
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "monitoring/grafana/dashboards/streaming-pipeline.json"
GENERATOR = ROOT / "monitoring/grafana/generate_dashboard.py"
PROMETHEUS = ROOT / "monitoring/prometheus/prometheus.yml"
COMPOSE = ROOT / "docker-compose.yml"


@pytest.fixture(scope="module")
def dashboard():
    return json.loads(DASHBOARD.read_text())


def test_committed_json_matches_the_generator(tmp_path):
    out = tmp_path / "dashboard.json"
    subprocess.run([sys.executable, str(GENERATOR), str(out)], check=True, capture_output=True)
    assert json.loads(out.read_text()) == json.loads(DASHBOARD.read_text()), \
        "Run `make grafana-dashboard` after editing generate_dashboard.py"


def test_dashboard_identity(dashboard):
    assert dashboard["uid"] == "streaming-pipeline"
    assert dashboard["refresh"] == "5s"


def test_panel_ids_are_unique(dashboard):
    ids = [p["id"] for p in dashboard["panels"]]
    assert len(ids) == len(set(ids))


def test_panels_fit_the_24_column_grid_without_overlap(dashboard):
    boxes = [(p["title"], p["gridPos"]) for p in dashboard["panels"]]
    for title, g in boxes:
        assert g["x"] >= 0 and g["w"] > 0 and g["x"] + g["w"] <= 24, title
    for (a, g1), (b, g2) in itertools.combinations(boxes, 2):
        overlap = (g1["x"] < g2["x"] + g2["w"] and g2["x"] < g1["x"] + g1["w"]
                   and g1["y"] < g2["y"] + g2["h"] and g2["y"] < g1["y"] + g1["h"])
        assert not overlap, f"{a} overlaps {b}"


def test_every_query_uses_the_provisioned_prometheus_datasource(dashboard):
    datasource = (ROOT / "monitoring/grafana/provisioning/datasources/prometheus.yml").read_text()
    uid = yaml.safe_load(datasource)["datasources"][0]["uid"]
    for panel in dashboard["panels"]:
        for target in panel.get("targets", []):
            assert target["datasource"]["uid"] == uid, panel["title"]
            assert target["expr"].strip(), panel["title"]


def test_queries_have_balanced_brackets(dashboard):
    for panel in dashboard["panels"]:
        for target in panel.get("targets", []):
            expr = target["expr"]
            for open_, close in ("()", "{}", "[]"):
                assert expr.count(open_) == expr.count(close), f"{panel['title']}: {expr}"


def test_prometheus_scrapes_services_that_exist_in_compose():
    services = set(yaml.safe_load(COMPOSE.read_text())["services"]) | {"localhost"}
    config = yaml.safe_load(PROMETHEUS.read_text())
    for job in config["scrape_configs"]:
        for static in job["static_configs"]:
            for target in static["targets"]:
                assert target.split(":")[0] in services, f"{job['job_name']}: {target}"
