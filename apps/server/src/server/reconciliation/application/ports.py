from __future__ import annotations

from typing import Protocol

from server.reconciliation.core.contribution import GatheredFacts
from server.reconciliation.core.findings import ReconciliationReport
from server.reconciliation.core.projection import ConceptMapping
from server.shared import Period


class FactProvider(Protocol):
    """Gathers every fact known about a client for a period.

    Deliberately a port rather than a direct call into intake: the
    reconciliation context must not depend on how documents are stored,
    classified or extracted, and the adapter that knows both sides lives at the
    composition edge.
    """

    def facts_for(self, client_id: str, period: Period, kind_id: str) -> GatheredFacts: ...


class ConceptMappingRepository(Protocol):
    """Stores how each document type's extracted fields become facts."""

    def save(self, mapping: ConceptMapping) -> None: ...
    def get(self, document_type_id: str, kind_id: str) -> ConceptMapping | None: ...
    def list_for_kind(self, kind_id: str) -> list[ConceptMapping]: ...
    def delete_for_document_type(self, document_type_id: str) -> None:
        """Drops this type's mappings, across every kind.

        Called when the type itself is deleted. Left behind they are
        unreachable — nothing lists mappings for a type that does not exist —
        and would silently attach to a type that happened to reuse the id.
        """
        ...


class ReconciliationReportRepository(Protocol):
    def save(self, report: ReconciliationReport) -> None: ...
    def get(self, report_id: str) -> ReconciliationReport | None: ...
    def get_latest(
        self, client_id: str, kind_id: str, period: Period
    ) -> ReconciliationReport | None: ...
