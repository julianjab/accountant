from __future__ import annotations

import logging
from dataclasses import dataclass

from server.reconciliation.application.ports import (
    ConceptMappingRepository,
    FactProvider,
    ReconciliationReportRepository,
)
from server.reconciliation.core.derivation import rules_from_mappings
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
        mappings: ConceptMappingRepository | None = None,
        engine: ReconciliationEngine | None = None,
    ) -> None:
        self._registry = registry
        self._facts = facts
        self._reports = reports
        self._mappings = mappings
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
            rules=self._rules_for(kind),
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

    def _rules_for(self, kind) -> tuple:
        """What the user configured first, then what the kind ships.

        A fact belongs to the first rule that claims it, so configuration
        outranks the built-in pack on purpose: the whole point of making this
        editable is that a person who reads the certificate can overrule a
        default that does not fit their documents.
        """
        configured: tuple = ()
        if self._mappings is not None:
            configured = rules_from_mappings(
                self._mappings.list_for_kind(kind.id), kind.concept_catalog()
            )
        return (*configured, *kind.rules())
