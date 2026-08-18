"""Warehouse tables.

Three schemas share one database. ``db_table`` carries the schema name with an
embedded quote pair, so Django emits ``"staging"."stg_delivery"`` and
``"dw"."fact_delivery"``. Staging columns are deliberately permissive: the
landing zone accepts whatever the source produced, and Transform is what makes
it trustworthy.
"""

import uuid

from django.db import models

PHASES = ("EXTRACT", "TRANSFORM", "LOAD")

TIME_BANDS = {
    **{hour: "MADRUGADA" for hour in range(0, 6)},
    **{hour: "MANANA" for hour in range(6, 7)},
    **{hour: "PICO_AM" for hour in range(7, 10)},
    **{hour: "MEDIODIA" for hour in range(10, 17)},
    **{hour: "PICO_PM" for hour in range(17, 20)},
    **{hour: "NOCHE" for hour in range(20, 24)},
}


class StagingRow(models.Model):
    """Common provenance columns for every landing table."""

    run_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    source_id = models.BigIntegerField(null=True)
    extracted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class StgCustomer(StagingRow):
    code = models.TextField(null=True)
    business_name = models.TextField(null=True)
    tax_id = models.TextField(null=True)
    city = models.TextField(null=True)
    state = models.TextField(null=True)
    customer_type = models.TextField(null=True)
    is_active = models.BooleanField(null=True)

    class Meta:
        db_table = 'staging"."stg_customer'


class StgVehicle(StagingRow):
    plate = models.TextField(null=True)
    economic_number = models.TextField(null=True)
    brand = models.TextField(null=True)
    model = models.TextField(null=True)
    year = models.IntegerField(null=True)
    vehicle_type = models.TextField(null=True)
    cargo_capacity_kg = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    fuel_type = models.TextField(null=True)
    is_active = models.BooleanField(null=True)

    class Meta:
        db_table = 'staging"."stg_vehicle'


class StgOperator(StagingRow):
    employee_number = models.TextField(null=True)
    first_name = models.TextField(null=True)
    last_name = models.TextField(null=True)
    license_type = models.TextField(null=True)
    hire_date = models.DateField(null=True)
    is_active = models.BooleanField(null=True)

    class Meta:
        db_table = 'staging"."stg_operator'


class StgRoute(StagingRow):
    code = models.TextField(null=True)
    name = models.TextField(null=True)
    origin_city = models.TextField(null=True)
    destination_city = models.TextField(null=True)
    distance_km = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    estimated_duration_min = models.IntegerField(null=True)
    route_type = models.TextField(null=True)
    zone = models.TextField(null=True)
    is_active = models.BooleanField(null=True)

    class Meta:
        db_table = 'staging"."stg_route'


class StgDelayCause(StagingRow):
    code = models.TextField(null=True)
    name = models.TextField(null=True)
    category = models.TextField(null=True)
    is_active = models.BooleanField(null=True)

    class Meta:
        db_table = 'staging"."stg_delay_cause'


class StgDelivery(StagingRow):
    folio = models.TextField(null=True)
    customer_code = models.TextField(null=True)
    route_code = models.TextField(null=True)
    vehicle_plate = models.TextField(null=True)
    operator_number = models.TextField(null=True)
    delay_cause_code = models.TextField(null=True)
    scheduled_departure = models.DateTimeField(null=True)
    actual_departure = models.DateTimeField(null=True)
    scheduled_arrival = models.DateTimeField(null=True)
    actual_arrival = models.DateTimeField(null=True)
    cargo_weight_kg = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    packages_count = models.IntegerField(null=True)
    declared_value = models.DecimalField(max_digits=16, decimal_places=2, null=True)
    freight_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    status = models.TextField(null=True)
    is_active = models.BooleanField(null=True)

    class Meta:
        db_table = 'staging"."stg_delivery'


class StgFuelLoad(StagingRow):
    folio = models.TextField(null=True)
    vehicle_plate = models.TextField(null=True)
    operator_number = models.TextField(null=True)
    load_datetime = models.DateTimeField(null=True)
    liters = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    price_per_liter = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    total_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    odometer_km = models.DecimalField(max_digits=16, decimal_places=2, null=True)
    is_active = models.BooleanField(null=True)

    class Meta:
        db_table = 'staging"."stg_fuel_load'


class StgMaintenance(StagingRow):
    folio = models.TextField(null=True)
    vehicle_plate = models.TextField(null=True)
    maintenance_type = models.TextField(null=True)
    service_date = models.DateField(null=True)
    odometer_km = models.DecimalField(max_digits=16, decimal_places=2, null=True)
    labor_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    parts_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    total_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    days_out_of_service = models.IntegerField(null=True)
    status = models.TextField(null=True)
    is_active = models.BooleanField(null=True)

    class Meta:
        db_table = 'staging"."stg_maintenance'


class DimDate(models.Model):
    date_key = models.IntegerField(primary_key=True)          # YYYYMMDD
    full_date = models.DateField(db_index=True)
    year = models.SmallIntegerField()
    quarter = models.SmallIntegerField()
    month = models.SmallIntegerField()
    month_name = models.CharField(max_length=12)
    week = models.SmallIntegerField()
    day = models.SmallIntegerField()
    day_of_week = models.SmallIntegerField()                  # 0 = Monday
    day_name = models.CharField(max_length=12)
    fortnight = models.SmallIntegerField()
    is_weekend = models.BooleanField()

    class Meta:
        db_table = 'dw"."dim_date'

    def __str__(self):
        return str(self.date_key)


class DimTime(models.Model):
    time_key = models.SmallIntegerField(primary_key=True)     # 0-23
    hour = models.SmallIntegerField()
    time_band = models.CharField(max_length=12)

    class Meta:
        db_table = 'dw"."dim_time'


class DimCustomer(models.Model):
    customer_key = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=10, unique=True)
    business_name = models.CharField(max_length=150)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80)
    customer_type = models.CharField(max_length=12)

    class Meta:
        db_table = 'dw"."dim_customer'


class DimVehicle(models.Model):
    vehicle_key = models.BigAutoField(primary_key=True)
    plate = models.CharField(max_length=10, unique=True)
    economic_number = models.CharField(max_length=10)
    brand = models.CharField(max_length=60)
    model = models.CharField(max_length=60)
    year = models.SmallIntegerField()
    vehicle_type = models.CharField(max_length=10)
    age_range = models.CharField(max_length=5)
    capacity_range = models.CharField(max_length=12)

    class Meta:
        db_table = 'dw"."dim_vehicle'


class DimOperator(models.Model):
    operator_key = models.BigAutoField(primary_key=True)
    employee_number = models.CharField(max_length=10, unique=True)
    full_name = models.CharField(max_length=160)
    license_type = models.CharField(max_length=2)
    seniority_range = models.CharField(max_length=8)

    class Meta:
        db_table = 'dw"."dim_operator'


class DimRoute(models.Model):
    route_key = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=150)
    origin_city = models.CharField(max_length=80)
    destination_city = models.CharField(max_length=80)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2)
    distance_range = models.CharField(max_length=12)
    route_type = models.CharField(max_length=10)
    zone = models.CharField(max_length=40)

    class Meta:
        db_table = 'dw"."dim_route'


class DimDelayCause(models.Model):
    delay_cause_key = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=80)
    category = models.CharField(max_length=10)

    class Meta:
        db_table = 'dw"."dim_delay_cause'


class FactDelivery(models.Model):
    """Grain: one delivery."""

    folio = models.CharField(max_length=14, unique=True)
    date = models.ForeignKey(DimDate, on_delete=models.PROTECT)
    time = models.ForeignKey(DimTime, on_delete=models.PROTECT)
    customer = models.ForeignKey(DimCustomer, on_delete=models.PROTECT)
    route = models.ForeignKey(DimRoute, on_delete=models.PROTECT)
    vehicle = models.ForeignKey(DimVehicle, on_delete=models.PROTECT)
    operator = models.ForeignKey(DimOperator, on_delete=models.PROTECT)
    delay_cause = models.ForeignKey(
        DimDelayCause, on_delete=models.PROTECT, null=True, blank=True
    )
    cargo_weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    packages_count = models.IntegerField()
    freight_cost = models.DecimalField(max_digits=10, decimal_places=2)
    planned_duration_min = models.IntegerField()
    actual_duration_min = models.IntegerField()
    delay_minutes = models.IntegerField()
    is_delayed = models.SmallIntegerField()
    distance_km = models.DecimalField(max_digits=8, decimal_places=2)
    cost_per_km = models.DecimalField(max_digits=10, decimal_places=4)

    class Meta:
        db_table = 'dw"."fact_delivery'
        indexes = [
            models.Index(fields=["date"], name="fd_date_idx"),
            models.Index(fields=["route"], name="fd_route_idx"),
            models.Index(fields=["vehicle"], name="fd_vehicle_idx"),
            models.Index(fields=["is_delayed"], name="fd_delayed_idx"),
        ]


class FactFuel(models.Model):
    """Grain: one refuelling event."""

    folio = models.CharField(max_length=14, unique=True)
    date = models.ForeignKey(DimDate, on_delete=models.PROTECT)
    time = models.ForeignKey(DimTime, on_delete=models.PROTECT)
    vehicle = models.ForeignKey(DimVehicle, on_delete=models.PROTECT)
    operator = models.ForeignKey(DimOperator, on_delete=models.PROTECT)
    liters = models.DecimalField(max_digits=8, decimal_places=2)
    price_per_liter = models.DecimalField(max_digits=6, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    km_traveled = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    efficiency_km_per_liter = models.DecimalField(
        max_digits=6, decimal_places=2, null=True
    )

    class Meta:
        db_table = 'dw"."fact_fuel'
        indexes = [
            models.Index(fields=["date"], name="ff_date_idx"),
            models.Index(fields=["vehicle"], name="ff_vehicle_idx"),
        ]


class FactMaintenance(models.Model):
    """Grain: one workshop order."""

    folio = models.CharField(max_length=14, unique=True)
    date = models.ForeignKey(DimDate, on_delete=models.PROTECT)
    vehicle = models.ForeignKey(DimVehicle, on_delete=models.PROTECT)
    maintenance_type = models.CharField(max_length=12)
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2)
    parts_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    days_out_of_service = models.SmallIntegerField()
    odometer_km = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'dw"."fact_maintenance'
        indexes = [
            models.Index(fields=["date"], name="fm_date_idx"),
            models.Index(fields=["vehicle"], name="fm_vehicle_idx"),
        ]


class EtlLog(models.Model):
    """One row per phase per table per run — the evidence the process ran."""

    run_id = models.UUIDField(db_index=True)
    phase = models.CharField(max_length=10)
    table_name = models.CharField(max_length=60)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True)
    rows_read = models.IntegerField(default=0)
    rows_written = models.IntegerField(default=0)
    rows_rejected = models.IntegerField(default=0)
    status = models.CharField(max_length=12, default="RUNNING")
    message = models.TextField(blank=True, default="")

    class Meta:
        db_table = 'dw"."etl_log'
        ordering = ["-started_at"]


class EtlError(models.Model):
    """Every rejected row, with the rule that rejected it. Nothing is dropped
    in silence."""

    run_id = models.UUIDField(db_index=True)
    source_table = models.CharField(max_length=60)
    source_pk = models.CharField(max_length=40, blank=True, default="")
    rule = models.CharField(max_length=60)
    description = models.TextField()
    raw_payload = models.JSONField(default=dict)
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dw"."etl_error'
        ordering = ["-detected_at"]
