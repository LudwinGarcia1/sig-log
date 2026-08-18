"""Run bookkeeping shared by the three ETL phases."""

import uuid
from contextlib import contextmanager

from django.utils import timezone

from warehouse.models import EtlError, EtlLog


class PhaseCounter:
    """Mutable tally a phase fills in while it works."""

    def __init__(self):
        self.read = 0
        self.written = 0
        self.rejected = 0


class EtlRun:
    """One invocation of the pipeline, identified by a UUID.

    Every log row and every rejected record carries this id, so a run can be
    audited end to end with a single ``WHERE run_id = ...``.
    """

    def __init__(self, full=False, since=None, rebuild=False):
        self.run_id = uuid.uuid4()
        self.full = full or rebuild
        self.rebuild = rebuild
        self._since = since

    @property
    def since(self):
        """Watermark for an incremental extract."""
        if self.full:
            return None
        return self._since or self.last_successful_run()

    def last_successful_run(self):
        latest = (
            EtlLog.objects.filter(phase="LOAD", status="SUCCESS")
            .order_by("-finished_at")
            .first()
        )
        return latest.finished_at if latest else None

    @contextmanager
    def phase(self, phase, table_name):
        """Open a log row, hand back a counter, close the row on exit."""
        log = EtlLog.objects.create(
            run_id=self.run_id,
            phase=phase,
            table_name=table_name,
            started_at=timezone.now(),
            status="RUNNING",
        )
        counter = PhaseCounter()
        try:
            yield counter
        except Exception as error:
            log.status = "FAILED"
            log.message = f"{type(error).__name__}: {error}"
            log.finished_at = timezone.now()
            log.rows_read = counter.read
            log.rows_written = counter.written
            log.rows_rejected = counter.rejected
            log.save()
            raise
        else:
            log.status = "SUCCESS"
            log.finished_at = timezone.now()
            log.rows_read = counter.read
            log.rows_written = counter.written
            log.rows_rejected = counter.rejected
            log.save()

    def reject(self, source_table, source_pk, rule, description, payload=None):
        """Quarantine a row. Never delete, never ignore."""
        EtlError.objects.create(
            run_id=self.run_id,
            source_table=source_table,
            source_pk=str(source_pk or ""),
            rule=rule,
            description=description,
            raw_payload=payload or {},
        )
