"""Date and time dimensions.

Both are conformed dimensions generated once from a range, not derived per
fact. ``dim_time`` exists so "horarios de mayor saturación" is a join, not an
EXTRACT() scattered through the reporting code.
"""

from datetime import timedelta

from warehouse.models import TIME_BANDS, DimDate, DimTime

MONTH_NAMES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
DAY_NAMES = [
    "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo",
]


def build_time_dimension():
    """Twenty-four rows, one per hour of the clock."""
    existing = set(DimTime.objects.values_list("time_key", flat=True))
    rows = [
        DimTime(time_key=hour, hour=hour, time_band=TIME_BANDS[hour])
        for hour in range(24)
        if hour not in existing
    ]
    DimTime.objects.bulk_create(rows)
    return DimTime.objects.count()


def build_date_dimension(start, end):
    """One row per calendar day in the inclusive range."""
    existing = set(DimDate.objects.values_list("date_key", flat=True))
    rows, current = [], start
    while current <= end:
        date_key = int(current.strftime("%Y%m%d"))
        if date_key not in existing:
            weekday = current.weekday()
            rows.append(DimDate(
                date_key=date_key,
                full_date=current,
                year=current.year,
                quarter=(current.month - 1) // 3 + 1,
                month=current.month,
                month_name=MONTH_NAMES[current.month - 1],
                week=int(current.strftime("%V")),
                day=current.day,
                day_of_week=weekday,
                day_name=DAY_NAMES[weekday],
                fortnight=1 if current.day <= 15 else 2,
                is_weekend=weekday >= 5,
            ))
        current += timedelta(days=1)
    DimDate.objects.bulk_create(rows, batch_size=1000)
    return DimDate.objects.count()
