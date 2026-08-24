"""Deleting a document type together with what reconciliation stored about it.

The same composition edge as `document_fact_provider`: intake owns the type
and reconciliation owns the mapping, and neither context may import the other.
Deleting one without the other is a real gap, so the step that joins them is a
named unit here rather than a couple of lines in a router — a router is not
somewhere a rule can be tested, and the next delete path would have to
remember it.
"""

from __future__ import annotations

import logging

from server.application.use_cases import DeleteDocumentType, DeleteDocumentTypeInput
from server.reconciliation.application.ports import ConceptMappingRepository

logger = logging.getLogger(__name__)


class DeleteDocumentTypeAndMappings:
    """Removes a document type and every concept mapping that referred to it."""

    def __init__(
        self,
        delete_document_type: DeleteDocumentType,
        mappings: ConceptMappingRepository,
    ) -> None:
        self._delete_document_type = delete_document_type
        self._mappings = mappings

    def execute(self, document_type_id: str) -> None:
        """Deletes the type, then its mappings.

        In that order, and not the other way round: a mapping deleted for a
        type whose own delete then failed would leave a type that extracts
        fields and reconciles nothing while still reading as configured. The
        reverse leaves a mapping nothing can reach, which changes no behaviour
        — nothing lists mappings for a type that does not exist.

        Whatever `DeleteDocumentType` raises travels out untouched: refusing
        because documents are filed under the type is an answer the caller
        acts on, not an error this layer can improve.
        """
        self._delete_document_type.execute(
            DeleteDocumentTypeInput(document_type_id=document_type_id)
        )
        try:
            self._mappings.delete_for_document_type(document_type_id)
        except Exception:
            # The type is already gone and there is no transaction across the
            # two contexts, so failing now would report an error for work that
            # succeeded. An unreachable mapping is worth a log, not a 500.
            logger.exception(
                "Deleted the document type but could not delete its concept mappings",
                extra={"document_type_id": document_type_id},
            )
