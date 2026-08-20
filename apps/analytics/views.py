"""Views for the Reportes y Análisis module.

Six screens: an executive dashboard, an operations panel, a costs panel, a
maintenance-alerts panel (reads the OLTP on purpose), a delay-prediction
screen and a route-clustering screen. Every screen degrades gracefully —
either the warehouse is empty (run_etl) or the ML artifacts are untrained
(train_models) — instead of raising.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.analytics import exports, queries
from apps.analytics.forms import DelayPredictionForm, PeriodForm
from apps.vehicles.services import maintenance_alerts
from ml import evaluation, supervised, unsupervised


def _period(request):
    """El periodo pedido por la URL, más el formulario para volver a pintarlo."""
    _, last_day = queries.data_bounds()
    form = PeriodForm(request.GET or None, last_day=last_day)
    period = form.period()
    return period, {
        "period_form": form,
        "period_label": period.label(),
        "period_query": request.GET.urlencode(),
    }


def _money(value):
    return f"${value:,.0f}"


@login_required
def dashboard(request):
    """Executive summary. Reads the warehouse, never the OLTP."""
    if queries.warehouse_is_empty():
        return render(
            request,
            "analytics/dashboard.html",
            {"section": "dashboard", "warehouse_empty": True},
        )

    period, period_context = _period(request)
    kpi = queries.kpi_summary(period)
    cards = [
        {"label": "Entregas del periodo", "value": f"{kpi['deliveries']:,}",
         "hint": period.label()},
        {"label": "Cumplimiento", "value": f"{kpi['on_time_rate']}%",
         "hint": "Llegadas dentro de la tolerancia de 15 min"},
        {"label": "Retraso promedio", "value": f"{kpi['avg_delay_minutes']} min",
         "hint": "Promedio sobre TODAS las entregas, puntuales incluidas"},
        {"label": "Retraso de las tardías", "value": f"{kpi['avg_delay_when_late']} min",
         "hint": f"Solo las {kpi['delayed']:,} que excedieron la tolerancia"},
        {"label": "Kilómetros recorridos", "value": f"{kpi['total_km']:,.0f}",
         "hint": "Suma de distancia por entrega"},
        {"label": "Ingreso por flete", "value": _money(kpi["total_freight"]),
         "hint": "Suma de fletes cobrados"},
        {"label": "Rendimiento medio", "value": f"{kpi['avg_efficiency']} km/L",
         "hint": "Promedio de la flotilla"},
        {"label": "Costo de combustible", "value": _money(kpi["fuel_cost"]),
         "hint": "Cargas registradas"},
        {"label": "Costo de mantenimiento", "value": _money(kpi["maintenance_cost"]),
         "hint": "Órdenes de taller"},
    ]

    return render(request, "analytics/dashboard.html", {
        "section": "dashboard",
        "warehouse_empty": False,
        "kpi": kpi,
        "cards": cards,
        **period_context,
        "trend_json": queries.monthly_trend(period),
        "cost_json": {
            "labels": ["Combustible", "Mantenimiento"],
            "values": [float(kpi["fuel_cost"]), float(kpi["maintenance_cost"])],
        },
    })


@login_required
def operations(request):
    """P1, P3, P4, P6 and P10, plus the service-demand mix, on one screen."""
    if queries.warehouse_is_empty():
        return render(request, "analytics/operations.html",
                      {"section": "operations", "warehouse_empty": True})

    period, period_context = _period(request)
    heatmap = queries.hour_heatmap(period)
    pareto = queries.delay_causes_pareto(period)
    top = queries.top_routes(limit=10, period=period)
    operators = queries.top_operators(limit=10, period=period)
    service_demand = queries.demand_by_service_type(period)

    return render(request, "analytics/operations.html", {
        "section": "operations",
        "warehouse_empty": False,
        **period_context,
        "top_routes": top,
        "worst_routes": queries.worst_routes(limit=10, period=period),
        "operators": operators,
        "heatmap": heatmap,
        "heatmap_json": heatmap,
        "pareto_json": pareto,
        "routes_json": {
            "labels": [row["code"] for row in top],
            "values": [row["shipments"] for row in top],
        },
        "operators_json": {
            "labels": [row["employee_number"] for row in operators],
            "values": [row["deliveries"] for row in operators],
        },
        "service_demand": service_demand,
        "service_demand_json": {
            "labels": [row["service_type"] for row in service_demand],
            "values": [row["shipments"] for row in service_demand],
        },
        "top_customers": queries.top_customers(limit=10, period=period),
    })


@login_required
def costs(request):
    """P2 and P5."""
    if queries.warehouse_is_empty():
        return render(request, "analytics/costs.html",
                      {"section": "costs", "warehouse_empty": True})

    period, period_context = _period(request)
    vehicles = queries.cost_by_vehicle(limit=15, period=period)
    efficiency = queries.efficiency_by_vehicle(limit=15, period=period)

    return render(request, "analytics/costs.html", {
        "section": "costs",
        "warehouse_empty": False,
        **period_context,
        "vehicles": vehicles,
        "efficiency": efficiency,
        "routes": queries.cost_per_km_by_route(limit=15, period=period),
        "cost_json": {
            "labels": [row["economic_number"] for row in vehicles],
            "fuel": [float(row["fuel_cost"]) for row in vehicles],
            "maintenance": [float(row["maintenance_cost"]) for row in vehicles],
        },
        "efficiency_json": {
            "labels": [row["economic_number"] for row in efficiency],
            "values": [row["efficiency"] for row in efficiency],
        },
    })


@login_required
def alerts(request):
    """P7 — reads the OLTP on purpose. See the spec, section 4.9."""
    rows = maintenance_alerts()
    return render(request, "analytics/alerts.html", {
        "section": "alerts",
        "warehouse_empty": False,
        "alerts": rows,
        "high": sum(1 for row in rows if row["severity"] == "ALTA"),
        "medium": sum(1 for row in rows if row["severity"] == "MEDIA"),
    })


@login_required
def predictions(request):
    """Unidad III in the UI: score a delivery and show how the model performs.

    Deviation from the brief: the brief's own view only inferred "untrained"
    from an empty metrics.json. That file is written once by train_models and
    never deleted alongside the .joblib artifacts, so a state with stale
    metrics but missing classifier/regressor files (exactly what
    UntrainedModelTest simulates) would render as if the models were still
    trained. Checking the artifact paths directly — the same technique the
    clusters() view below already uses for CLUSTER_PATH — closes that gap.
    """
    form = DelayPredictionForm(request.POST or None)
    prediction, error = None, None
    trained = supervised.CLASSIFIER_PATH.exists() and supervised.REGRESSOR_PATH.exists()

    if request.method == "POST" and form.is_valid():
        try:
            prediction = supervised.predict_delay(form.to_features())
        except FileNotFoundError as failure:
            error = str(failure)

    metrics = evaluation.load_metrics()
    if not trained or not metrics:
        error = error or (
            "Los modelos no están entrenados. Ejecuta "
            "'python manage.py train_models' para generarlos."
        )

    return render(request, "analytics/predictions.html", {
        "section": "predictions",
        "warehouse_empty": False,
        "form": form,
        "prediction": prediction,
        "error": error,
        "metrics": metrics.get("classification"),
        "regression": metrics.get("regression"),
    })


@login_required
def clusters(request):
    """Unidad IV in the UI: the PCA plane and the profile of every group."""
    prepared = unsupervised.load_clusters()
    if prepared is None:
        return render(request, "analytics/clusters.html", {
            "section": "clusters",
            "warehouse_empty": False,
            "error": (
                "El modelo de agrupamiento no está entrenado. Ejecuta "
                "'python manage.py train_models' para generarlo."
            ),
        })

    metrics = evaluation.load_metrics().get("clustering", {})

    return render(request, "analytics/clusters.html", {
        "section": "clusters",
        "warehouse_empty": False,
        "error": None,
        "metrics": metrics,
        "summary": prepared["summary"],
        "scatter_json": prepared["scatter"],
        "explained": [
            round(value * 100, 1) for value in metrics.get("explained_variance", [])
        ],
    })


@login_required
def export_report(request, slug, fmt):
    """Serve a report as CSV or Excel, honouring the period on the screen."""
    period, _ = _period(request)
    if fmt == "xlsx":
        return exports.to_excel(slug, period)
    return exports.to_csv(slug, period)
