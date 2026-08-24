from __future__ import annotations

from server.reconciliation.core.findings import ReconciliationReport
from server.reconciliation.core.projection import ConceptMapping
from server.shared import Period


class InMemoryConceptMappingRepository:
    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], ConceptMapping] = {}

    def save(self, mapping: ConceptMapping) -> None:
        self._by_key[(mapping.document_type_id, mapping.kind_id)] = mapping

    def get(self, document_type_id: str, kind_id: str) -> ConceptMapping | None:
        return self._by_key.get((document_type_id, kind_id))

    def list_for_kind(self, kind_id: str) -> list[ConceptMapping]:
        return [m for (_, k), m in self._by_key.items() if k == kind_id]

    def delete_for_document_type(self, document_type_id: str) -> None:
        for key in [k for k in self._by_key if k[0] == document_type_id]:
            del self._by_key[key]


class InMemoryReconciliationReportRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, ReconciliationReport] = {}

    def save(self, report: ReconciliationReport) -> None:
        self._by_id[report.id] = report

    def get(self, report_id: str) -> ReconciliationReport | None:
        return self._by_id.get(report_id)

    def get_latest(
        self, client_id: str, kind_id: str, period: Period
    ) -> ReconciliationReport | None:
        matches = [
            r
            for r in self._by_id.values()
            if r.client_id == client_id and r.kind_id == kind_id and r.period == period
        ]
        if not matches:
            return None
        return max(matches, key=lambda r: r.generated_at)
