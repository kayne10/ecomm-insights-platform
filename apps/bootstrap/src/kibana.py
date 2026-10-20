"""
Create Kibana data views and the "Ecomm Insights" dashboard. Safe to re-run (overwrites).

Everything is generated from code so the dashboard is reproducible on any machine:
    make dashboards        ->  http://localhost:5601/app/dashboards#/view/ecomm-insights

Visualizations are Lens saved objects built with the small helpers below. To change a
panel, edit its definition in `panels()` and re-run; to tweak it by hand in Kibana, use
"Save as" so a re-run doesn't overwrite your copy.
"""
import json
import sys
import time

import requests
from common.registry import EVENT_REGISTRY
from common.settings import KibanaConfig

KIBANA = KibanaConfig.URL
HEADERS = {"kbn-xsrf": "true", "Content-Type": "application/json"}
DATA_VIEW_ID = "ecomm-events"
DASHBOARD_ID = "ecomm-insights"

# EUI visualization palette, so colours match the rest of Kibana.
GREEN, BLUE, PINK, PURPLE, YELLOW, ORANGE, RED = (
    "#54B399", "#6092C0", "#D36086", "#9170B8", "#D6BF57", "#DA8B45", "#E7664C")

USD = {"id": "custom", "params": {"pattern": "$0,0.[00]"}}
USD_SHORT = {"id": "custom", "params": {"pattern": "$0.0a"}}
INT = {"id": "number", "params": {"decimals": 0}}


def kql(query):
    return {"query": query, "language": "kuery"}


def is_event(name):
    return kql(f'event_type : "{name}"')


# --- Lens column builders -----------------------------------------------------

def count(label, filter=None, fmt=INT):
    col = {"label": label, "customLabel": True, "dataType": "number", "operationType": "count",
           "isBucketed": False, "scale": "ratio", "sourceField": "___records___",
           "params": {"emptyAsNull": False, "format": fmt}}
    if filter:
        col["filter"] = filter
    return col


def metric(op, field, label, filter=None, fmt=INT):
    col = {"label": label, "customLabel": True, "dataType": "number", "operationType": op,
           "isBucketed": False, "scale": "ratio", "sourceField": field,
           "params": {"emptyAsNull": True, "format": fmt}}
    if filter:
        col["filter"] = filter
    return col


def date_histogram():
    return {"label": "@timestamp", "dataType": "date", "operationType": "date_histogram",
            "sourceField": "@timestamp", "isBucketed": True, "scale": "interval",
            "params": {"interval": "auto", "includeEmptyRows": True, "dropPartials": False}}


def terms(field, label, order_by, size=10, other=False):
    return {"label": label, "customLabel": True, "dataType": "string", "operationType": "terms",
            "sourceField": field, "isBucketed": True, "scale": "ordinal",
            "params": {"size": size, "orderBy": {"type": "column", "columnId": order_by},
                       "orderDirection": "desc", "otherBucket": other, "missingBucket": False,
                       "parentFormat": {"id": "terms"}, "include": [], "exclude": [],
                       "includeIsRegex": False, "excludeIsRegex": False}}


def numeric_terms(field, label, order_desc=False):
    col = terms(field, label, order_by=None)
    col["dataType"] = "number"
    col["params"]["orderBy"] = {"type": "alphabetical", "fallback": True}
    col["params"]["orderDirection"] = "desc" if order_desc else "asc"
    col["params"]["parentFormat"] = {"id": "terms"}
    return col


def filters(label, named_queries):
    return {"label": label, "customLabel": True, "dataType": "string", "operationType": "filters",
            "isBucketed": True, "scale": "ordinal",
            "params": {"filters": [{"label": lbl, "input": q} for lbl, q in named_queries]}}


def ratio_formula(label, numerator_kql, denominator_kql, col_id):
    """A Lens formula `count(kql=a) / count(kql=b)`, expanded into the helper columns Lens stores."""
    formula = f"count(kql='{numerator_kql}') / count(kql='{denominator_kql}')"
    x0, x1, x2 = f"{col_id}X0", f"{col_id}X1", f"{col_id}X2"
    helper = lambda q: {  # noqa: E731
        "label": f"Part of {label}", "customLabel": True, "dataType": "number",
        "operationType": "count", "isBucketed": False, "scale": "ratio",
        "sourceField": "___records___", "filter": kql(q), "params": {"emptyAsNull": False}}
    return {
        col_id: {"label": label, "customLabel": True, "dataType": "number", "operationType": "formula",
                 "isBucketed": False, "scale": "ratio", "references": [x2],
                 "params": {"formula": formula, "isFormulaBroken": False,
                            "format": {"id": "percent", "params": {"decimals": 1}}}},
        x0: helper(numerator_kql),
        x1: helper(denominator_kql),
        x2: {"label": f"Part of {label}", "customLabel": True, "dataType": "number",
             "operationType": "math", "isBucketed": False, "scale": "ratio", "references": [x0, x1],
             "params": {"tinymathAst": {"type": "function", "name": "divide", "args": [x0, x1],
                                        "location": {"min": 0, "max": len(formula)}, "text": formula}}},
    }


# --- Lens visualization builders ----------------------------------------------

def column_order(columns):
    """Lens requires bucket (group-by) columns before metric columns."""
    return sorted(columns, key=lambda c: not columns[c]["isBucketed"])


def lens(title, vis_type, columns, visualization, query=""):
    layer = {"columns": columns, "columnOrder": column_order(columns), "incompleteColumns": {}}
    return {
        "title": title,
        "visualizationType": vis_type,
        "state": {
            "datasourceStates": {"formBased": {"layers": {"layer1": layer}}},
            "visualization": visualization,
            "query": kql(query),
            "filters": [],
            "internalReferences": [],
            "adHocDataViews": {},
        },
    }


def kpi(title, column, color, subtitle):
    return kpi_columns(title, {"value": column}, color, subtitle)


def kpi_columns(title, columns, color, subtitle):
    """Metric tile. The first column is the displayed value; any others are formula helpers."""
    return lens(title, "lnsMetric", columns, {
        "layerId": "layer1", "layerType": "data", "metricAccessor": next(iter(columns)),
        "color": color, "subtitle": subtitle, "showBar": False, "titlesTextAlign": "left",
        "valuesTextAlign": "left", "valueFontMode": "default",
    })


def xy(title, series_type, x, y, split=None, legend="right", y_title=None,
       x_title=None, color=None, value_labels=False):
    columns = {"x": x, "y": y}
    layer = {"layerId": "layer1", "layerType": "data", "seriesType": series_type, "xAccessor": "x",
             "accessors": ["y"], "position": "top", "showGridlines": False}
    if split:
        columns["split"] = split
        layer["splitAccessor"] = "split"
        layer["palette"] = {"type": "palette", "name": "default"}
    elif color:
        layer["yConfig"] = [{"forAccessor": "y", "color": color}]
    return lens(title, "lnsXY", columns, {
        "legend": {"isVisible": bool(split), "position": legend, "showSingleSeries": False,
                   "shouldTruncate": True, "maxLines": 1},
        "valueLabels": "show" if value_labels else "hide", "preferredSeriesType": series_type, "fittingFunction": "Zero",
        "curveType": "CURVE_MONOTONE_X", "emphasizeFitting": True, "endValue": "None",
        "gridlinesVisibilitySettings": {"x": False, "yLeft": True, "yRight": True},
        "tickLabelsVisibilitySettings": {"x": True, "yLeft": True, "yRight": True},
        "axisTitlesVisibilitySettings": {"x": x_title is not None, "yLeft": y_title is not None,
                                         "yRight": False},
        "xTitle": x_title or "", "yTitle": y_title or "",
        "layers": [layer],
    })


def donut(title, group, value):
    return lens(title, "lnsPie", {"group": group, "value": value}, {
        "shape": "donut", "palette": {"type": "palette", "name": "default"},
        "layers": [{"layerId": "layer1", "layerType": "data", "primaryGroups": ["group"],
                    "metrics": ["value"], "numberDisplay": "percent", "categoryDisplay": "default",
                    "legendDisplay": "hide", "legendPosition": "right", "nestedLegend": False,
                    "emptySizeRatio": 0.5}],
    })


def table(title, columns, sort_by):
    return lens(title, "lnsDatatable", columns, {
        "layerId": "layer1", "layerType": "data",
        "columns": [{"columnId": c, "isTransposed": False} for c in columns],
        "sorting": {"columnId": sort_by, "direction": "desc"},
        "paging": {"enabled": True, "size": 10},
        "rowHeight": "single", "headerRowHeight": "single",
    })


def tagcloud(title, tag, value):
    return lens(title, "lnsTagcloud", {"tag": tag, "value": value}, {
        "layerId": "layer1", "tagAccessor": "tag", "valueAccessor": "value",
        "maxFontSize": 48, "minFontSize": 14, "orientation": "single", "showLabel": False,
        "palette": {"type": "palette", "name": "default"},
    })


# --- The dashboard ------------------------------------------------------------

def panels():
    """(id, grid position, lens attributes). The grid is 48 columns wide."""
    purchase, refund, review = is_event("purchase"), is_event("refund"), is_event("product_review")
    p = []

    # Row 1: KPIs
    p.append(("kpi-revenue", (0, 0, 8, 6), kpi(
        "Revenue", metric("sum", "amount", "Revenue", purchase, USD), GREEN, "from purchases")))
    p.append(("kpi-orders", (8, 0, 8, 6), kpi(
        "Orders", count("Orders", purchase), BLUE, "purchases")))
    p.append(("kpi-aov", (16, 0, 8, 6), kpi(
        "Avg order value", metric("average", "amount", "Avg order value", purchase, USD), PURPLE,
        "revenue / orders")))
    p.append(("kpi-conversion", (24, 0, 8, 6), kpi_columns(
        "View to purchase",
        ratio_formula("View to purchase", 'event_type : "purchase"', 'event_type : "product_view"',
                      "conv"),
        YELLOW, "purchases / product views")))
    p.append(("kpi-refunds", (32, 0, 8, 6), kpi(
        "Refunded", metric("sum", "amount", "Refunded", refund, USD), RED, "from refunds")))
    p.append(("kpi-rating", (40, 0, 8, 6), kpi(
        "Avg rating", metric("average", "rating", "Avg rating", review,
                             {"id": "number", "params": {"decimals": 2, "suffix": " ★"}}),
        ORANGE, "from product reviews")))

    # Row 2: traffic and funnel
    p.append(("events-over-time", (0, 6, 30, 13), xy(
        # Stacked bars, not areas: area charts interpolate across idle periods and invent traffic.
        "Live event stream by type", "bar_stacked", date_histogram(), count("Events"),
        split=terms("event_type", "Event type", "y", size=10))))
    p.append(("funnel", (30, 6, 18, 13), xy(
        "Shopping funnel", "bar_horizontal",
        filters("Stage", [
            ("1 · Viewed product", is_event("product_view")),
            ("2 · Added to cart", is_event("add_to_cart")),
            ("3 · Started checkout", is_event("checkout_started")),
            ("4 · Purchased", is_event("purchase")),
        ]),
        count("Events"), color=BLUE, value_labels=True)))

    # Row 3: money
    p.append(("revenue-over-time", (0, 19, 24, 12), xy(
        "Revenue over time", "bar", date_histogram(),
        metric("sum", "amount", "Revenue", purchase, USD_SHORT), color=GREEN)))
    p.append(("top-customers", (24, 19, 24, 12), table(
        "Top customers by spend",
        {"customer": terms("user_id", "Customer", "spend", size=10),
         "spend": metric("sum", "amount", "Total spend", purchase, USD),
         "orders": count("Orders", purchase),
         # Every metric here uses the purchase filter: Lens scopes the table's buckets to the
         # sort column's filter, so a metric over another event type would always read 0.
         "aov": metric("average", "amount", "Avg order", purchase, USD)},
        sort_by="spend")))

    # Row 4: why customers leave or love it
    p.append(("refund-reasons", (0, 31, 16, 12), donut(
        "Refund reasons", terms("reason", "Reason", "value", size=10),
        count("Refunds", refund))))
    p.append(("ratings", (16, 31, 16, 12), xy(
        "Review ratings", "bar", numeric_terms("rating", "Stars", order_desc=True),
        count("Reviews", review), color=ORANGE)))
    p.append(("search-terms", (32, 31, 16, 12), tagcloud(
        "Top searches", terms("query.keyword", "Search term", "value", size=12),
        count("Searches", is_event("search")))))

    # Row 5: product and category insights
    p.append(("viewed-categories", (0, 43, 16, 12), donut(
        "Product views by category", terms("category", "Category", "value", size=10),
        count("Views", is_event("product_view")))))
    p.append(("top-carted", (16, 43, 16, 12), xy(
        "Most added-to-cart products", "bar_horizontal",
        terms("product_id", "Product", "y", size=8), count("Cart adds", is_event("add_to_cart")),
        color=PURPLE)))
    p.append(("refunded-categories", (32, 43, 16, 12), xy(
        "Refunded revenue by category", "bar_horizontal",
        terms("category", "Category", "y", size=8),
        metric("sum", "amount", "Refunded", refund, USD), color=RED)))
    return p


# --- Kibana API -----------------------------------------------------------------

def api(method, path, body=None):
    r = requests.request(method, f"{KIBANA}{path}", headers=HEADERS,
                         data=json.dumps(body) if body is not None else None)
    if not r.ok:
        raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text}")
    return r.json()


def wait_for_kibana(timeout=180):
    print(f"[Kibana] Waiting for {KIBANA}", end="", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status = requests.get(f"{KIBANA}/api/status", timeout=5).json()
            if status["status"]["overall"]["level"] == "available":
                print(" ✅")
                return
        except Exception:
            pass
        print(".", end="", flush=True)
        time.sleep(3)
    sys.exit(" ❌ Kibana did not become available")


def save(obj_type, obj_id, attributes, references=()):
    api("POST", f"/api/saved_objects/{obj_type}/{obj_id}?overwrite=true",
        {"attributes": attributes, "references": list(references)})


def create_data_views():
    aliases = {"events": "All events"}
    for domain in sorted({cls.domain for cls in EVENT_REGISTRY.values()}):
        aliases[f"events-{domain}"] = f"{domain.title()} events"
    for alias, name in aliases.items():
        view_id = DATA_VIEW_ID if alias == "events" else f"ecomm-{alias}"
        save("index-pattern", view_id, {"title": alias, "name": name, "timeFieldName": "@timestamp"})
        print(f"[Kibana] ✅ Data view: {name} ({alias})")


def create_dashboard():
    layer_ref = {"type": "index-pattern", "id": DATA_VIEW_ID,
                 "name": "indexpattern-datasource-layer-layer1"}
    grid, refs = [], []
    for panel_id, (x, y, w, h), attributes in panels():
        lens_id = f"{DASHBOARD_ID}-{panel_id}"
        save("lens", lens_id, attributes, [layer_ref])
        config = {"enhancements": {}}
        if attributes["visualizationType"] == "lnsMetric":
            config["hidePanelTitles"] = True  # the metric tile already shows its title
        grid.append({"type": "lens", "panelIndex": panel_id, "panelRefName": f"panel_{panel_id}",
                     "gridData": {"x": x, "y": y, "w": w, "h": h, "i": panel_id},
                     "embeddableConfig": config})
        refs.append({"type": "lens", "id": lens_id, "name": f"{panel_id}:panel_{panel_id}"})

    save("dashboard", DASHBOARD_ID, {
        "title": "🛒 Ecomm Insights",
        "description": "Live e-commerce events from Kafka, via the Elasticsearch sinks. "
                       "Generated by apps/bootstrap/src/kibana.py (make dashboards).",
        "panelsJSON": json.dumps(grid),
        "optionsJSON": json.dumps({"useMargins": True, "syncColors": True, "syncCursor": True,
                                   "syncTooltips": True, "hidePanelTitles": False}),
        "timeRestore": True, "timeFrom": "now-30m", "timeTo": "now",
        "refreshInterval": {"pause": False, "value": 10000},
        "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps({"query": kql(""), "filter": []})},
    }, refs)
    print(f"[Kibana] ✅ Dashboard with {len(grid)} panels: "
          f"http://localhost:5601/app/dashboards#/view/{DASHBOARD_ID}")


if __name__ == "__main__":
    wait_for_kibana()
    create_data_views()
    create_dashboard()
