from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from server.shared import FactRole


@dataclass(frozen=True, slots=True)
class Concept:
    """A named thing an amount can be reported *for*.

    Concept ids are namespaced by the kind that owns them (`dian:...`,
    `bank:...`) so two reconciliation models can coexist in one catalog without
    colliding.
    """

    id: str
    label: str
    role: FactRole
    description: str = ""


class UnknownConcept(KeyError):
    pass


class ConceptCatalog:
    """The vocabulary of one reconciliation kind.

    Two audiences read this: the engine, to label findings, and the document
    type configuration UI, which offers `evidence_concepts()` as the list an
    extracted field can be mapped onto. That second use is why the catalog is
    published by the kind rather than hardcoded in intake — it is the seam
    that lets a new reconciliation model bring its own vocabulary.
    """

    def __init__(self, concepts: Iterable[Concept]) -> None:
        self._by_id: dict[str, Concept] = {}
        for concept in concepts:
            if concept.id in self._by_id:
                raise ValueError(f"Duplicate concept id: {concept.id}")
            self._by_id[concept.id] = concept

    def __contains__(self, concept_id: object) -> bool:
        return concept_id in self._by_id

    def __len__(self) -> int:
        return len(self._by_id)

    def get(self, concept_id: str) -> Concept:
        try:
            return self._by_id[concept_id]
        except KeyError as exc:
            raise UnknownConcept(concept_id) from exc

    def label(self, concept_id: str) -> str:
        """The concept's label, falling back to its id.

        Findings must stay renderable for concepts the catalog has not been
        taught yet — an exogena row wording nobody has curated still has to
        reach the accountant's screen.
        """
        concept = self._by_id.get(concept_id)
        return concept.label if concept is not None else concept_id

    def of_role(self, role: FactRole) -> tuple[Concept, ...]:
        return tuple(c for c in self._by_id.values() if c.role is role)

    @property
    def spine_concepts(self) -> tuple[Concept, ...]:
        return self.of_role(FactRole.SPINE)

    @property
    def evidence_concepts(self) -> tuple[Concept, ...]:
        return self.of_role(FactRole.EVIDENCE)

    def merged_with(self, other: ConceptCatalog) -> ConceptCatalog:
        return ConceptCatalog([*self._by_id.values(), *other._by_id.values()])
