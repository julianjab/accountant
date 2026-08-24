from __future__ import annotations

import logging
from dataclasses import dataclass

from server.reconciliation.application.ports import FactProvider, ReconciliationReportRepository
from server.reconciliation.core.engine import ReconciliationEngine
from server.reconciliation.core.findings import ReconciliationReport, report_id_for
from server.reconciliation.core.registry import KindRegistry
from server.shared import Period

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ReconcileClientPeriodInput:
    client_id: str
    kind_id: str
    period: Period


class ReconcileClientPeriod:
    """Rebuilds a client's reconciliation report for one period.

    Always a full rebuild rather than an incremental update. Every document
    that arrives can change how earlier ones reconcile — a certificate turns
    five MISSING_EVIDENCE lines into one match — and a report assembled from
    partial updates would drift out of step with the documents it claims to
    summarize. Reconciliation is arithmetic over a few dozen facts, so the
    rebuild is cheap and the report is always exactly what the current
    documents support.
    """

    def __init__(
        self,
        registry: KindRegistry,
        facts: FactProvider,
        reports: ReconciliationReportRepository,
        engine: ReconciliationEngine | None = None,
    ) -> None:
        self._registry = registry
        self._facts = facts
        self._reports = reports
        self._engine = engine or ReconciliationEngine()

    def execute(self, data: ReconcileClientPeriodInput) -> ReconciliationReport:
        kind = self._registry.get(data.kind_id)
        if data.period.granularity is not kind.period_granularity:
            raise ValueError(
                f"{kind.id} reconciles by {kind.period_granularity}, "
                f"but {data.period} is a {data.period.granularity} period"
            )

        gathered = self._facts.facts_for(data.client_id, data.period, kind.id)
        report = self._engine.reconcile(
            kind=kind,
            client_id=data.client_id,
            period=data.period,
            facts=gathered.facts,
            report_id=report_id_for(data.client_id, kind.id, data.period),
            contributions=gathered.contributions,
        )
        self._reports.save(report)
        logger.info(
            "Reconciled client period",
            extra={
                "client_id": data.client_id,
                "kind_id": kind.id,
                "period": data.period.key,
                "findings": report.summary.total_findings,
                "needing_attention": report.summary.needing_attention,
            },
        )
        return report
