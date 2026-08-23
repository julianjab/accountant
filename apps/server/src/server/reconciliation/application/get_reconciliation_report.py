from __future__ import annotations

from dataclasses import dataclass

from server.reconciliation.application.ports import ReconciliationReportRepository
from server.reconciliation.core.findings import ReconciliationReport
from server.reconciliation.core.registry import KindRegistry
from server.shared import Period


@dataclass(frozen=True, slots=True)
class GetReconciliationReportInput:
    client_id: str
    kind_id: str
    period: Period


class GetReconciliationReport:
    """Reads back the last report computed for a client and period.

    Deliberately does not reconcile on a miss. A read that silently ran the
    engine would make an expensive, document-mutating operation happen on a
    page load, and would hide from the caller that no reconciliation has been
    run yet — which is itself the answer they need.
    """

    def __init__(self, registry: KindRegistry, reports: ReconciliationReportRepository) -> None:
        self._registry = registry
        self._reports = reports

    def execute(self, data: GetReconciliationReportInput) -> ReconciliationReport | None:
        kind = self._registry.get(data.kind_id)
        return self._reports.get_latest(data.client_id, kind.id, data.period)
