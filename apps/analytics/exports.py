"""Tabular exports of the analytical reports.

Each report declares its Spanish column headers next to the key that produces
them, so CSV and Excel stay in step with the on-screen tables.
"""

import csv
from io import BytesIO

import pandas as pd
from django.http import Http404, HttpResponse

from apps.analytics import queries

REPORTS = {
    "rutas": {
        "label": "Rutas más utilizadas",
        "builder": lambda: queries.top_routes(limit=100),
        "columns": [
            ("code", "Código"), ("name", "Ruta"), ("zone", "Zona"),
            ("shipments", "Envíos"), ("delay_rate", "% retraso"),
        ],
    },
    "rutas-retrasadas": {
        "label": "Rutas con mayores retrasos",
        "builder": lambda: queries.worst_routes(limit=100),
        "columns": [
            ("code", "Código"), ("name", "Ruta"), ("zone", "Zona"),
            ("shipments", "Envíos"), ("avg_delay", "Retraso promedio (min)"),
            ("delay_rate", "% retraso"),
        ],
    },
    "operadores": {
        "label": "Operadores con más entregas",
        "builder": lambda: queries.top_operators(limit=100),
        "columns": [
            ("employee_number", "Empleado"), ("full_name", "Nombre"),
            ("deliveries", "Entregas"), ("delay_rate", "% retraso"),
        ],
    },
    "costos-vehiculo": {
        "label": "Costo total por vehículo",
        "builder": lambda: queries.cost_by_vehicle(limit=200),
        "columns": [
            ("economic_number", "Económico"), ("plate", "Placa"),
            ("vehicle_type", "Tipo"), ("age_range", "Antigüedad"),
            ("fuel_cost", "Combustible"), ("maintenance_cost", "Mantenimiento"),
            ("total_cost", "Total"),
        ],
    },
    "rendimiento": {
        "label": "Rendimiento por vehículo",
        "builder": lambda: queries.efficiency_by_vehicle(limit=200),
        "columns": [
            ("economic_number", "Económico"), ("vehicle_type", "Tipo"),
            ("age_range", "Antigüedad"), ("efficiency", "km/L"),
            ("liters", "Litros"),
        ],
    },
    "demanda-servicio": {
        "label": "Demanda por tipo de servicio",
        "builder": queries.demand_by_service_type,
        "columns": [
            ("service_type", "Servicio"), ("shipments", "Envíos"),
            ("share", "Participación %"), ("delay_rate", "% retraso"),
            ("freight", "Flete"), ("routes", "Rutas"),
        ],
    },
    "demanda-cliente": {
        "label": "Clientes con mayor demanda",
        "builder": lambda: queries.top_customers(limit=200),
        "columns": [
            ("code", "Código"), ("business_name", "Cliente"),
            ("city", "Ciudad"), ("customer_type", "Tipo"),
            ("shipments", "Envíos"), ("delay_rate", "% retraso"),
            ("freight", "Flete"),
        ],
    },
    "costo-por-km": {
        "label": "Costo por kilómetro por ruta",
        "builder": lambda: queries.cost_per_km_by_route(limit=200),
        "columns": [
            ("code", "Código"), ("name", "Ruta"),
            ("cost_per_km", "Costo por km"), ("shipments", "Envíos"),
        ],
    },
}


def _report_or_404(slug):
    if slug not in REPORTS:
        raise Http404(f"Reporte desconocido: {slug}")
    return REPORTS[slug]


def to_csv(slug):
    report = _report_or_404(slug)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{slug}.csv"'
    response.write("\ufeff")  # BOM para que Excel lea los acentos
    writer = csv.writer(response)
    writer.writerow([header for _, header in report["columns"]])
    for row in report["builder"]():
        writer.writerow([row[key] for key, _ in report["columns"]])
    return response


def to_excel(slug):
    report = _report_or_404(slug)
    frame = pd.DataFrame(
        [
            {header: row[key] for key, header in report["columns"]}
            for row in report["builder"]()
        ]
    )
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name=report["label"][:31])
    buffer.seek(0)

    response = HttpResponse(
        buffer.read(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = f'attachment; filename="{slug}.xlsx"'
    return response
