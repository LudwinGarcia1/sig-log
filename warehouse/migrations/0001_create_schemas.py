from django.db import migrations


class Migration(migrations.Migration):
    """Create the schemas before any warehouse table is built.

    Every later warehouse migration depends on this one, so the schemas always
    exist by the time Django emits CREATE TABLE "dw"."...".
    """

    initial = True
    dependencies = []

    operations = [
        migrations.RunSQL(
            sql=[
                "CREATE SCHEMA IF NOT EXISTS staging;",
                "CREATE SCHEMA IF NOT EXISTS dw;",
            ],
            reverse_sql=[
                "DROP SCHEMA IF EXISTS staging CASCADE;",
                "DROP SCHEMA IF EXISTS dw CASCADE;",
            ],
        ),
    ]
