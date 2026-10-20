import itertools
import json

import pytest

from common.registry import EVENT_REGISTRY

GRID_COLUMNS = 48


@pytest.fixture
def kibana(app_module):
    return app_module("bootstrap", "kibana")


@pytest.fixture
def panels(kibana):
    return kibana.panels()


def layer_columns(attributes):
    return attributes["state"]["datasourceStates"]["formBased"]["layers"]["layer1"]


def accessor_ids(attributes):
    """Column ids a visualization refers to, per Lens visualization type."""
    vis = attributes["state"]["visualization"]
    kind = attributes["visualizationType"]
    if kind == "lnsMetric":
        return [vis["metricAccessor"]]
    if kind == "lnsXY":
        layer = vis["layers"][0]
        return [layer["xAccessor"], *layer["accessors"], *filter(None, [layer.get("splitAccessor")])]
    if kind == "lnsPie":
        layer = vis["layers"][0]
        return [*layer["primaryGroups"], *layer["metrics"]]
    if kind == "lnsDatatable":
        return [c["columnId"] for c in vis["columns"]] + [vis["sorting"]["columnId"]]
    if kind == "lnsTagcloud":
        return [vis["tagAccessor"], vis["valueAccessor"]]
    raise AssertionError(f"Unknown visualization type {kind}")


def test_panel_ids_are_unique(panels):
    ids = [panel_id for panel_id, _, _ in panels]
    assert len(ids) == len(set(ids))


def test_panels_fit_the_grid_without_overlapping(panels):
    boxes = [(pid, x, y, w, h) for pid, (x, y, w, h), _ in panels]
    for pid, x, y, w, h in boxes:
        assert x >= 0 and w > 0 and x + w <= GRID_COLUMNS, pid
    for (a, ax, ay, aw, ah), (b, bx, by, bw, bh) in itertools.combinations(boxes, 2):
        overlap = ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah
        assert not overlap, f"{a} overlaps {b}"


def test_bucket_columns_come_before_metrics(panels):
    # Lens errors with "Provided column name or index is invalid" otherwise.
    for pid, _, attributes in panels:
        layer = layer_columns(attributes)
        bucketed = [layer["columns"][c]["isBucketed"] for c in layer["columnOrder"]]
        assert bucketed == sorted(bucketed, reverse=True), pid


def test_visualizations_only_reference_existing_columns(panels):
    for pid, _, attributes in panels:
        columns = layer_columns(attributes)["columns"]
        for column_id in accessor_ids(attributes):
            assert column_id in columns, f"{pid} refers to missing column {column_id}"


def test_formula_helper_columns_are_resolvable(panels):
    for pid, _, attributes in panels:
        columns = layer_columns(attributes)["columns"]
        for column in columns.values():
            for ref in column.get("references", []):
                assert ref in columns, f"{pid}: {ref}"


def test_table_metrics_share_the_sort_columns_filter(panels):
    # Lens scopes a table's buckets to the sort column's filter, so any metric with a
    # different filter silently reads 0 (this happened with a "Cart adds" column).
    for pid, _, attributes in panels:
        if attributes["visualizationType"] != "lnsDatatable":
            continue
        columns = layer_columns(attributes)["columns"]
        sort_filter = columns[attributes["state"]["visualization"]["sorting"]["columnId"]].get("filter")
        for column_id, column in columns.items():
            if not column["isBucketed"]:
                assert column.get("filter") == sort_filter, f"{pid}.{column_id}"


def test_filters_only_reference_registered_event_types(panels):
    names = set(EVENT_REGISTRY)
    for pid, _, attributes in panels:
        text = json.dumps(attributes)
        for chunk in text.split('event_type : \\"')[1:]:
            assert chunk.split('\\"')[0] in names, pid


def test_ratio_formula_expands_into_lens_helper_columns(kibana):
    columns = kibana.ratio_formula("Rate", "a : 1", "b : 2", "r")

    assert set(columns) == {"r", "rX0", "rX1", "rX2"}
    assert columns["r"]["operationType"] == "formula"
    assert columns["r"]["references"] == ["rX2"]
    assert columns["rX2"]["references"] == ["rX0", "rX1"]
    assert columns["rX0"]["filter"]["query"] == "a : 1"
    assert columns["rX1"]["filter"]["query"] == "b : 2"


def test_column_order_puts_buckets_first(kibana):
    columns = {"m": {"isBucketed": False}, "b": {"isBucketed": True}}
    assert kibana.column_order(columns) == ["b", "m"]


def test_dashboard_references_every_panel_and_hides_kpi_titles(kibana, panels, monkeypatch):
    saved = []
    monkeypatch.setattr(kibana, "save", lambda *args: saved.append(args))

    kibana.create_dashboard()

    obj_type, obj_id, attributes, references = saved[-1]
    assert (obj_type, obj_id) == ("dashboard", "ecomm-insights")
    grid = json.loads(attributes["panelsJSON"])
    assert len(grid) == len(panels) == len(references)
    assert {r["name"] for r in references} == {f"{g['panelIndex']}:{g['panelRefName']}" for g in grid}
    kpis = {pid for pid, _, a in panels if a["visualizationType"] == "lnsMetric"}
    for g in grid:
        assert g["embeddableConfig"].get("hidePanelTitles", False) == (g["panelIndex"] in kpis)
    assert attributes["refreshInterval"] == {"pause": False, "value": 10000}


def test_lens_objects_point_at_the_events_data_view(kibana, monkeypatch):
    saved = []
    monkeypatch.setattr(kibana, "save", lambda *args: saved.append(args))

    kibana.create_dashboard()

    for obj_type, _, _, references in saved:
        if obj_type == "lens":
            assert references == [{"type": "index-pattern", "id": "ecomm-events",
                                   "name": "indexpattern-datasource-layer-layer1"}]


def test_a_data_view_per_search_alias(kibana, monkeypatch):
    saved = []
    monkeypatch.setattr(kibana, "save", lambda *args: saved.append(args))

    kibana.create_data_views()

    titles = {attrs["title"] for _, _, attrs, *_ in saved}
    domains = {cls.domain for cls in EVENT_REGISTRY.values()}
    assert titles == {"events"} | {f"events-{d}" for d in domains}
    assert all(attrs["timeFieldName"] == "@timestamp" for _, _, attrs, *_ in saved)
