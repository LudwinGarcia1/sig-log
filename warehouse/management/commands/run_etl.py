"""Run the three ETL phases end to end."""

from django.core.management.base import BaseCommand

from warehouse.etl.context import EtlRun
from warehouse.etl.extract import run as run_extract
from warehouse.etl.load import run as run_load
from warehouse.etl.transform import run as run_transform
from warehouse.models import EtlError


class Command(BaseCommand):
    help = (
        "Ejecuta el proceso ETL: extracción, transformación y carga. "
        "Sin argumentos realiza una extracción incremental."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--full", action="store_true",
            help="Extracción completa: arrastra todo el histórico.",
        )
        parser.add_argument(
            "--rebuild", action="store_true",
            help="Vacía dimensiones y hechos y luego ejecuta una carga completa.",
        )

    def handle(self, *args, **options):
        verbose = options["verbosity"] > 0
        etl_run = EtlRun(full=options["full"], rebuild=options["rebuild"])
        mode = (
            "reconstrucción" if etl_run.rebuild
            else "completa" if etl_run.full else "incremental"
        )
        if verbose:
            self.stdout.write(f"Corrida {etl_run.run_id} — extracción {mode}.")

        extracted = run_extract(etl_run)
        if verbose:
            self.stdout.write("  EXTRACT  " + self._summary(extracted))

        transformed = run_transform(etl_run)
        if verbose:
            self.stdout.write(
                "  TRANSFORM "
                + self._summary({k: len(v) for k, v in transformed.items()})
            )

        loaded = run_load(etl_run, transformed)
        if verbose:
            self.stdout.write("  LOAD     " + self._summary(loaded))

        rejected = EtlError.objects.filter(run_id=etl_run.run_id).count()
        if verbose:
            style = self.style.WARNING if rejected else self.style.SUCCESS
            self.stdout.write(style(
                f"ETL finalizado. Registros en cuarentena: {rejected}. "
                f"Consulta dw.etl_error con run_id = '{etl_run.run_id}'."
            ))

    @staticmethod
    def _summary(counts):
        return ", ".join(f"{name}={value}" for name, value in sorted(counts.items()))
