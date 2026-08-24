"""Reconciling a client the moment one of their documents is approved.

The third composition edge, alongside `document_fact_provider` and
`document_type_deletion`: intake owns the act of naming a document, and
reconciliation owns what that document then means. Neither context may import
the other, so the step that joins them is a named unit here.

Why it exists at all: `GetReconciliationReport` deliberately does not
reconcile on a miss, because a page load must not trigger expensive work and
because "no reconciliation has been run" is itself an answer. That reasoning
covers reads. It does not cover this: a person has just approved a document,
which is the act that decides what the client's figures are, and every screen
that would show them what the client still owes reads a report that does not
exist yet. Leaving them to find a button elsewhere makes the system look like
it did nothing with what they just did.
"""

from __future__ import annotations

import logging

from server.application.use_cases import (
    ApprovedDocument,
    ApproveDocument,
    ApproveDocumentInput,
)
from server.reconciliation.application.reconcile_client_period import (
    ReconcileClientPeriod,
    ReconcileClientPeriodInput,
)
from server.reconciliation.core.registry import KindRegistry
from server.shared import Period

logger = logging.getLogger(__name__)


class ApproveDocumentAndReconcile:
    """Approves a document, then rebuilds the reports it just changed."""

    def __init__(
        self,
        approve: ApproveDocument,
        reconcile: ReconcileClientPeriod,
        registry: KindRegistry,
    ) -> None:
        self._approve = approve
        self._reconcile = reconcile
        self._registry = registry

    def execute(self, data: ApproveDocumentInput) -> ApprovedDocument:
        """Whatever `ApproveDocument` raises travels out untouched: a document
        nothing could be read from is an answer the caller acts on, and
        nothing was reconciled because nothing was approved.
        """
        approved = self._approve.execute(data)
        self._reconcile_periods(approved)
        return approved

    def _reconcile_periods(self, approved: ApprovedDocument) -> None:
        kind_id = self._kind_owning(approved.document.source_id)
        if kind_id is None:
            # Either a format no reconciliation model owns, or an ordinary
            # document extracted by OCR — whose figures reach a report through
            # its type's concept mapping, on the next run of that report,
            # rather than through a parser this side knows about.
            return

        # The periods come from the file, not from the caller: a client's
        # folder holds several years, and the report that went stale is the one
        # for the year this document actually covers.
        for key in approved.periods:
            try:
                self._reconcile.execute(
                    ReconcileClientPeriodInput(
                        client_id=approved.document.client_id,
                        kind_id=kind_id,
                        period=Period.parse(key),
                    )
                )
            except Exception:
                # The approval already succeeded and is persisted. Failing the
                # request now would report an error for work that was done, and
                # would leave the caller believing the document was not
                # approved. The reconciliation stays re-runnable on its own.
                logger.exception(
                    "Approved the document but could not reconcile the period it covers",
                    extra={
                        "document_id": approved.document.id,
                        "client_id": approved.document.client_id,
                        "kind_id": kind_id,
                        "period": key,
                    },
                )

    def _kind_owning(self, source_id: str | None) -> str | None:
        """Which reconciliation model declares this source.

        Resolved through the registry rather than passed in, so intake never
        has to know that reconciliation kinds exist — it only ever handed back
        an opaque source id.
        """
        for kind in self._registry.all():
            if any(source.id == source_id for source in kind.sources()):
                return kind.id
        return None
