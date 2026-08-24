"""Reconciling a client the moment their spine document is recognised.

The third composition edge, alongside `document_fact_provider` and
`document_type_deletion`: intake owns the act of naming a document, and
reconciliation owns what that document then means. Neither context may import
the other, so the step that joins them is a named unit here.

Why it exists at all: `GetReconciliationReport` deliberately does not
reconcile on a miss, because a page load must not trigger expensive work and
because "no reconciliation has been run" is itself an answer. That reasoning
covers reads. It does not cover this: someone has just told the system which
file is the exogena, which is the one document the whole reconciliation is
built around, and every screen that would show them what the client still
owes reads a report that does not exist yet. Leaving them to find a button
elsewhere makes the system look like it did nothing with what they just said.
"""

from __future__ import annotations

import logging

from server.application.use_cases import (
    RecognizedDocument,
    RecognizeDocumentSource,
    RecognizeDocumentSourceInput,
)
from server.reconciliation.application.reconcile_client_period import (
    ReconcileClientPeriod,
    ReconcileClientPeriodInput,
)
from server.reconciliation.core.registry import KindRegistry
from server.shared import Period

logger = logging.getLogger(__name__)


class RecognizeDocumentSourceAndReconcile:
    """Recognises a document, then rebuilds the reports it just changed."""

    def __init__(
        self,
        recognize: RecognizeDocumentSource,
        reconcile: ReconcileClientPeriod,
        registry: KindRegistry,
    ) -> None:
        self._recognize = recognize
        self._reconcile = reconcile
        self._registry = registry

    def execute(self, data: RecognizeDocumentSourceInput) -> RecognizedDocument:
        """Whatever `RecognizeDocumentSource` raises travels out untouched: a
        file that is not the source it was said to be is an answer the caller
        acts on, and nothing was reconciled because nothing was recognised.
        """
        recognized = self._recognize.execute(data)
        self._reconcile_periods(recognized)
        return recognized

    def _reconcile_periods(self, recognized: RecognizedDocument) -> None:
        kind_id = self._kind_owning(recognized.document.source_id)
        if kind_id is None:
            # A parsed format that belongs to no reconciliation model. Nothing
            # to rebuild; the document was still recognised.
            return

        # The periods come from the file, not from the caller: a client's
        # folder holds several years, and the report that went stale is the one
        # for the year this report actually covers.
        for key in recognized.periods:
            try:
                self._reconcile.execute(
                    ReconcileClientPeriodInput(
                        client_id=recognized.document.client_id,
                        kind_id=kind_id,
                        period=Period.parse(key),
                    )
                )
            except Exception:
                # The recognition already succeeded and is persisted. Failing
                # the request now would report an error for work that was done,
                # and would leave the caller believing the file was not read.
                # The reconciliation stays re-runnable from its own screen.
                logger.exception(
                    "Recognised the document but could not reconcile the period it covers",
                    extra={
                        "document_id": recognized.document.id,
                        "client_id": recognized.document.client_id,
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
