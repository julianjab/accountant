from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from server.reconciliation.core.concepts import ConceptCatalog
from server.reconciliation.core.rules import ReconciliationRule
from server.shared import FactRole, FinancialFact, Period, PeriodGranularity, TaxId


@dataclass(frozen=True, slots=True)
class SourceContent:
    """Bytes handed to a kind's extractor, with what it needs to stamp facts.

    Intentionally not intake's `DocumentContent`: the reconciliation context
    must not depend on intake, and the adapter that bridges the two is a
    three-line translation at the edge. That small duplication is what keeps
    the dependency arrow pointing one way.
    """

    data: bytes
    media_type: str
    file_name: str
    source_id: str
    subject_tax_id: TaxId | None = None
    period: Period | None = None


class SourceNotRecognized(ValueError):
    """Raised by an extractor handed bytes that are not its format.

    Distinct from a genuine parse failure: a client's folder holds every kind
    of spreadsheet, so "this is not an exogena report" is an ordinary outcome
    to move past, while "this is an exogena report and it is malformed" must
    surface.
    """


class FactExtractor(Protocol):
    """Turns a source document straight into facts, with no AI in the path.

    Used where the format is structured and exact — a spreadsheet the tax
    authority generated. Running a language model over a sixty-row financial
    table buys nothing and can invent figures the whole report then rests on.
    """

    def extract(self, content: SourceContent) -> tuple[FinancialFact, ...]: ...


@dataclass(frozen=True, slots=True)
class FactSourceSpec:
    """A document a reconciliation kind expects, and how it becomes facts."""

    id: str
    label: str
    role: FactRole
    media_types: frozenset[str]
    #: None means the facts come from the generic path — OCR extraction plus
    #: the document type's concept mapping — rather than a dedicated parser.
    extractor: FactExtractor | None = None
    #: Whether the reconciliation is meaningful without this source at all.
    required: bool = False


@runtime_checkable
class ReconciliationKind(Protocol):
    """One reconciliation model: its vocabulary, its rules, its inputs.

    Adding a model means implementing this and registering it. Nothing in
    `reconciliation.core` may import a concrete kind, and nothing in a kind may
    be reached by name from anywhere but the registry — those two constraints
    together are what make the seam real rather than decorative.
    """

    @property
    def id(self) -> str: ...

    @property
    def label(self) -> str: ...

    @property
    def period_granularity(self) -> PeriodGranularity: ...

    def concept_catalog(self) -> ConceptCatalog: ...

    def rules(self) -> tuple[ReconciliationRule, ...]: ...

    def sources(self) -> tuple[FactSourceSpec, ...]: ...
