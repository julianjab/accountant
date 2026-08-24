from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from server.domain.entities import DocumentType
from server.domain.ports.document_storage import DocumentContent


class DocumentClassifier(Protocol):
    """Fast AI: given a document and the available document types, picks the right one."""

    def classify(
        self, content: DocumentContent, available_types: list[DocumentType]
    ) -> DocumentType | None: ...


class OcrEngine(Protocol):
    """Runs the OCR/extraction configured for a document type."""

    def extract(self, content: DocumentContent, document_type: DocumentType) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class ConceptOption:
    """One entry of the vocabulary an extracted field may be mapped onto.

    Plain data rather than a reconciliation type on purpose: this module is in
    the domain, which must not know that reconciliation exists. The caller
    flattens whichever catalog applies into these before asking.
    """

    id: str
    label: str
    description: str = ""


class FieldRole(StrEnum):
    """What a proposed field is for, so a person can be shown the few that
    matter instead of twenty they must triage themselves.

    Most of a certificate is context — addresses, cities, legal notices. What
    an accountant needs is the identifier that ties the paper to a party, and
    the figures.
    """

    #: A tax number, account number or document number.
    IDENTIFIER = "identifier"
    #: A monetary figure.
    AMOUNT = "amount"
    #: A date, a name, an address, a notice.
    CONTEXT = "context"


@dataclass(frozen=True, slots=True)
class ProposedField:
    """One field of the proposed schema, with what it is and what it holds."""

    path: str
    label: str
    role: FieldRole
    #: The value read from the sample, so a person can recognise the field
    #: without opening the document beside the screen.
    sample_value: str = ""


@dataclass(frozen=True, slots=True)
class ProposedFieldMapping:
    """A field of the proposed schema, tied to the concept it represents."""

    field_path: str
    concept_id: str
    #: Where the account this amount belongs to sits, when the document says.
    account_path: str | None = None
    #: -1 when the document states the figure with the opposite sign to the
    #: concept (a charge presented as a positive number, say).
    sign: int = 1

    def __post_init__(self) -> None:
        if self.sign not in (1, -1):
            raise ValueError(f"A field mapping's sign must be +1 or -1, not {self.sign}")


@dataclass(frozen=True, slots=True)
class ProposedOcrConfig:
    extraction_prompt: str
    extraction_schema: dict[str, Any]
    #: How the schema's fields line up with the vocabulary offered. Empty when
    #: no vocabulary was supplied.
    field_mappings: tuple[ProposedFieldMapping, ...] = ()
    #: Fields the AI deliberately left unmapped, with its reason. These still
    #: get extracted; they just cannot be reconciled. Surfaced rather than
    #: dropped so the gap is a visible decision instead of a silent omission.
    unmapped_fields: tuple[tuple[str, str], ...] = ()
    #: Where the document states who is reporting the amounts. Without it no
    #: fact can be attributed to anyone, and every mapped field is discarded —
    #: so a mapping is only as useful as this.
    reporter_path: str | None = None
    reporter_name_path: str | None = None
    #: Where the document states the period it covers, so a certificate for
    #: one year cannot reconcile against another.
    period_path: str | None = None
    #: Every field the schema declares, classified. Empty when the AI did
    #: not say, which a caller reads as "offer them all, preselect nothing".
    fields: tuple[ProposedField, ...] = ()


class DocumentTypeConfigurator(Protocol):
    """AI that, given a sample document, proposes the extraction prompt + schema
    for a new document type (Config > Document type)."""

    def propose_config(
        self,
        content: DocumentContent,
        type_name: str,
        concepts: Sequence[ConceptOption] = (),
    ) -> ProposedOcrConfig:
        """Proposes how to extract this kind of document, and — when a
        vocabulary is offered — what each extracted field means.

        Both in one call, not two. The model has the document in front of it
        and has just invented those field names; that is the only moment when
        tying them to concepts is trivial. A second call would re-derive both
        sides independently and could disagree with itself about the names it
        produced.
        """
        ...
