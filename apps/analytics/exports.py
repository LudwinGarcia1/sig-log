"""Tabular exports of the analytical reports.

Each report declares its Spanish column headers next to the key that produces
them, so CSV, Excel and PDF stay in step with the on-screen tables.

The PDF is built with reportlab because it is a pure-Python wheel: WeasyPrint
renders nicer type but needs GTK installed on Windows, which would break the
from-scratch installation the manuals promise.
"""

import csv
from io import BytesIO

import pandas as pd
from django.http import Http404, HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from apps.analytics import queries

REPORTS = {
    "rutas": {
        "label": "Rutas más utilizadas",
        "builder": lambda period=None: queries.top_routes(limit=100, period=period),
        "columns": [
            ("code", "Código"), ("name", "Ruta"), ("zone", "Zona"),
            ("shipments", "Envíos"), ("delay_rate", "% retraso"),
        ],
    },
    "rutas-retrasadas": {
        "label": "Rutas con mayores retrasos",
        "builder": lambda period=None: queries.worst_routes(limit=100, period=period),
        "columns": [
            ("code", "Código"), ("name", "Ruta"), ("zone", "Zona"),
            ("shipments", "Envíos"), ("avg_delay", "Retraso promedio (min)"),
            ("delay_rate", "% retraso"),
        ],
    },
    "operadores": {
        "label": "Operadores con más entregas",
        "builder": lambda period=None: queries.top_operators(limit=100, period=period),
        "columns": [
            ("employee_number", "Empleado"), ("full_name", "Nombre"),
            ("deliveries", "Entregas"), ("delay_rate", "% retraso"),
        ],
    },
    "costos-vehiculo": {
        "label": "Costo total por vehículo",
        "builder": lambda period=None: queries.cost_by_vehicle(limit=200, period=period),
        "columns": [
            ("economic_number", "Económico"), ("plate", "Placa"),
            ("vehicle_type", "Tipo"), ("age_range", "Antigüedad"),
            ("fuel_cost", "Combustible"), ("maintenance_cost", "Mantenimiento"),
            ("total_cost", "Total"),
        ],
    },
    "rendimiento": {
        "label": "Rendimiento por vehículo",
        "builder": lambda period=None: queries.efficiency_by_vehicle(limit=200, period=period),
        "columns": [
            ("economic_number", "Económico"), ("vehicle_type", "Tipo"),
            ("age_range", "Antigüedad"), ("efficiency", "km/L"),
            ("liters", "Litros"),
        ],
    },
    "demanda-servicio": {
        "label": "Demanda por tipo de servicio",
        "builder": lambda period=None: queries.demand_by_service_type(period),
        "columns": [
            ("service_type", "Servicio"), ("shipments", "Envíos"),
            ("share", "Participación %"), ("delay_rate", "% retraso"),
            ("freight", "Flete"), ("routes", "Rutas"),
        ],
    },
    "demanda-cliente": {
        "label": "Clientes con mayor demanda",
        "builder": lambda period=None: queries.top_customers(limit=200, period=period),
        "columns": [
            ("code", "Código"), ("business_name", "Cliente"),
            ("city", "Ciudad"), ("customer_type", "Tipo"),
            ("shipments", "Envíos"), ("delay_rate", "% retraso"),
            ("freight", "Flete"),
        ],
    },
    "costo-por-km": {
        "label": "Costo por kilómetro por ruta",
        "builder": lambda period=None: queries.cost_per_km_by_route(limit=200, period=period),
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


def to_csv(slug, period=None):
    report = _report_or_404(slug)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{slug}.csv"'
    response.write("\ufeff")  # BOM para que Excel lea los acentos
    writer = csv.writer(response)
    writer.writerow([header for _, header in report["columns"]])
    for row in report["builder"](period):
        writer.writerow([row[key] for key, _ in report["columns"]])
    return response


def to_excel(slug, period=None):
    report = _report_or_404(slug)
    frame = pd.DataFrame(
        [
            {header: row[key] for key, header in report["columns"]}
            for row in report["builder"](period)
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


# Paleta del PDF, alineada con la del sitio (static/js/charts.js).
PDF_HEADER_BG = colors.HexColor("#0d6efd")
PDF_STRIPE_BG = colors.HexColor("#f2f5fa")
PDF_LINE = colors.HexColor("#c8d1dc")


def _pdf_styles():
    sheet = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "SiglogTitle", parent=sheet["Title"], fontSize=16, spaceAfter=2,
            alignment=0, textColor=colors.HexColor("#212529"),
        ),
        "meta": ParagraphStyle(
            "SiglogMeta", parent=sheet["Normal"], fontSize=9,
            textColor=colors.HexColor("#6c757d"),
        ),
        "cell": ParagraphStyle(
            "SiglogCell", parent=sheet["Normal"], fontSize=8, leading=10,
        ),
        "head": ParagraphStyle(
            "SiglogHead", parent=sheet["Normal"], fontSize=8, leading=10,
            textColor=colors.white, fontName="Helvetica-Bold",
        ),
        "right": ParagraphStyle(
            "SiglogRight", parent=sheet["Normal"], fontSize=8, leading=10,
            alignment=TA_RIGHT,
        ),
    }


def _stamp(canvas, doc):
    """Pie de página: quién lo generó, cuándo, y el número de página."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#6c757d"))
    canvas.drawString(15 * mm, 10 * mm, "SIG-LOG — Sistema Integral de Gestión Logística")
    canvas.drawRightString(
        doc.pagesize[0] - 15 * mm, 10 * mm, f"Página {canvas.getPageNumber()}"
    )
    canvas.restoreState()


def pdf_bytes(slug, period=None):
    """El reporte como PDF horizontal, con encabezado repetido por página."""
    report = _report_or_404(slug)
    styles = _pdf_styles()
    rows = report["builder"](period)

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=14 * mm, bottomMargin=18 * mm,
        title=report["label"], author="SIG-LOG",
    )

    generated = timezone.localtime().strftime("%d/%m/%Y %H:%M")
    period_text = (period or queries.Period()).label()
    story = [
        Paragraph(report["label"], styles["title"]),
        Paragraph(
            f"Periodo: {period_text} · {len(rows)} registros · "
            f"generado el {generated}",
            styles["meta"],
        ),
        Spacer(1, 6 * mm),
    ]

    if not rows:
        story.append(Paragraph(
            "No hay datos en el periodo seleccionado.", styles["cell"]
        ))
    else:
        # La primera columna se alinea a la izquierda y el resto a la derecha:
        # son códigos contra cantidades.
        header = [Paragraph(title, styles["head"]) for _, title in report["columns"]]
        body = [
            [
                Paragraph(
                    f"{row[key]}", styles["cell"] if index == 0 else styles["right"]
                )
                for index, (key, _) in enumerate(report["columns"])
            ]
            for row in rows
        ]
        table = Table([header] + body, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PDF_HEADER_BG),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.4, PDF_LINE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PDF_STRIPE_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(table)

    document.build(story, onFirstPage=_stamp, onLaterPages=_stamp)
    buffer.seek(0)
    return buffer.read()


def to_pdf(slug, period=None):
    response = HttpResponse(pdf_bytes(slug, period), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{slug}.pdf"'
    return response
