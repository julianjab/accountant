from __future__ import annotations

from dataclasses import dataclass

from server.reconciliation.application.ports import ConceptMappingRepository
from server.reconciliation.core.projection import ConceptMapping
from server.reconciliation.core.registry import KindRegistry


class UnknownMappedConcept(ValueError):
    """A mapping names a concept the kind's catalog does not define."""


@dataclass(frozen=True, slots=True)
class SaveConceptMappingInput:
    mapping: ConceptMapping


class SaveConceptMapping:
    """Records how a document type's extracted fields become reconcilable facts.

    Every concept is validated against the kind's catalog before the mapping is
    stored. A typo in a concept id would otherwise be accepted silently and
    then produce facts no rule ever selects: the certificate would look mapped,
    the claim it was meant to satisfy would stay reported as missing, and
    nothing would point at the mapping as the cause.
    """

    def __init__(self, registry: KindRegistry, mappings: ConceptMappingRepository) -> None:
        self._registry = registry
        self._mappings = mappings

    def execute(self, data: SaveConceptMappingInput) -> ConceptMapping:
        kind = self._registry.get(data.mapping.kind_id)
        catalog = kind.concept_catalog()
        unknown = sorted(
            {e.concept_id for e in data.mapping.entries if e.concept_id not in catalog}
        )
        if unknown:
            raise UnknownMappedConcept(
                f"{kind.id} does not define concept(s): {', '.join(unknown)}"
            )
        self._mappings.save(data.mapping)
        return data.mapping
