from django.db import connection
from django.test import TestCase

from warehouse import models as dw


class SchemaPlacementTest(TestCase):
    """The three-schema split is the backbone of Unidad II; assert it holds."""

    def test_staging_models_live_in_the_staging_schema(self):
        for model in (dw.StgCustomer, dw.StgDelivery, dw.StgFuelLoad):
            self.assertTrue(
                model._meta.db_table.startswith('staging"."'),
                f"{model.__name__} is not in the staging schema",
            )

    def test_warehouse_models_live_in_the_dw_schema(self):
        for model in (dw.DimRoute, dw.FactDelivery, dw.EtlLog):
            self.assertTrue(
                model._meta.db_table.startswith('dw"."'),
                f"{model.__name__} is not in the dw schema",
            )

    def test_schemas_exist_in_the_database(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name IN ('staging', 'dw')"
            )
            found = {row[0] for row in cursor.fetchall()}
        self.assertEqual(found, {"staging", "dw"})

    def test_fact_delivery_carries_every_dimension_key(self):
        field_names = {field.name for field in dw.FactDelivery._meta.get_fields()}
        self.assertTrue(
            {
                "date", "time", "customer", "route",
                "vehicle", "operator", "delay_cause",
            }.issubset(field_names)
        )

    def test_fact_delivery_measures_are_present(self):
        field_names = {field.name for field in dw.FactDelivery._meta.get_fields()}
        self.assertTrue(
            {
                "cargo_weight_kg", "packages_count", "freight_cost",
                "planned_duration_min", "actual_duration_min",
                "delay_minutes", "is_delayed", "distance_km", "cost_per_km",
            }.issubset(field_names)
        )

    def test_dim_time_bands_cover_the_clock(self):
        self.assertEqual(len(dw.TIME_BANDS), 24)
        self.assertEqual(dw.TIME_BANDS[8], "PICO_AM")
        self.assertEqual(dw.TIME_BANDS[18], "PICO_PM")
        self.assertEqual(dw.TIME_BANDS[3], "MADRUGADA")
