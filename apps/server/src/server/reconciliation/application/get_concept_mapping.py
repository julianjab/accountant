from __future__ import annotations

from dataclasses import dataclass

from server.reconciliation.application.ports import ConceptMappingRepository
from server.reconciliation.core.projection import ConceptMapping
from server.reconciliation.core.registry import KindRegistry


@dataclass(frozen=True, slots=True)
class GetConceptMappingInput:
    document_type_id: str
    kind_id: str


class GetConceptMapping:
    """Reads back how a document type's fields map onto a kind's vocabulary.

    Resolves the kind first so an unknown one is told apart from a document
    type that simply has no mapping yet: the caller has to distinguish "you
    asked for a reconciliation model that does not exist" from "this document
    type is not mapped", and they lead to different fixes.
    """

    def __init__(self, registry: KindRegistry, mappings: ConceptMappingRepository) -> None:
        self._registry = registry
        self._mappings = mappings

    def execute(self, data: GetConceptMappingInput) -> ConceptMapping | None:
        kind = self._registry.get(data.kind_id)
        return self._mappings.get(data.document_type_id, kind.id)
