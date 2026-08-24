from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from server.domain.entities import DocumentType, FieldRole
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


@dataclass(frozen=True, slots=True)
class ExistingConfig:
    """The configuration a proposal is meant to improve rather than replace.

    A type that missed a row of a table needs its schema widened, not a second
    schema invented beside it: every concept mapping someone curated is keyed
    by path, so a regeneration that renames the fields it keeps throws all of
    them away to fix one omission.
    """

    extraction_prompt: str
    extraction_schema: dict[str, Any]


@dataclass(frozen=True, slots=True)
class KeptField:
    """A field a person kept from the last reading, in their words.

    The label travels because it is the vocabulary the type is read in: a
    person who renames "Valor GMF" to "GMF retenido" has told the model what
    this field is called on their desk, which is worth more to the next
    reading than the heading the paper happens to print. The note is the same
    act at a finer grain — "this is a row of the table, not the total" is
    exactly the correction a schema that collapsed a table needs, and saying
    it against the field it concerns beats saying it in a paragraph the model
    has to match back to a path on its own.
    """

    path: str
    label: str = ""
    note: str = ""


@dataclass(frozen=True, slots=True)
class FieldSelection:
    """What a person kept from the last reading, and what they threw out.

    The point of the loop: a proposal is an offer, and the answer to it is
    itself the best instruction for the next one. Without this, each round
    started from the document alone and re-proposed what had just been
    rejected, so converging on the handful of fields an accountant actually
    wants meant pruning the same twenty fields again every time.

    Empty means a first reading, with nothing behind it to honour.
    """

    kept: tuple[KeptField, ...] = ()
    #: Paths the person removed on purpose. Distinct from a path nobody
    #: mentioned: this one was offered, looked at, and refused.
    dropped: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.kept or self.dropped)


@dataclass(frozen=True, slots=True)
class ProposedField:
    """One field of the proposed schema, with what it is and what it holds."""

    path: str
    label: str
    role: FieldRole
    #: The value read from the sample, so a person can recognise the field
    #: without opening the document beside the screen.
    sample_value: str = ""
    #: The part of the document this field came from, named as the document
    #: names it. A certificate is already divided into blocks on paper —
    #: withholdings, balances, issuer details — and choosing fields block by
    #: block is the same act as reading it. Empty when the AI did not say.
    section: str = ""


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
        guidance: str = "",
        base: ExistingConfig | None = None,
        selection: FieldSelection | None = None,
    ) -> ProposedOcrConfig:
        """Proposes how to extract this kind of document, and — when a
        vocabulary is offered — what each extracted field means.

        Both in one call, not two. The model has the document in front of it
        and has just invented those field names; that is the only moment when
        tying them to concepts is trivial. A second call would re-derive both
        sides independently and could disagree with itself about the names it
        produced.

        `guidance` is what the person configuring the type says is wrong with
        what they got: a certificate whose table has a row per obligation is
        read as one row until someone says so, and no amount of re-running the
        same request finds the row that was never asked for.

        `base` makes it a revision instead of a fresh reading: the existing
        paths must survive, because the mappings are keyed by them.
        """
        ...

    def describe_fields(
        self,
        content: DocumentContent,
        type_name: str,
        paths: Sequence[str],
    ) -> tuple[ProposedField, ...]:
        """Describes the fields a type already declares, reading the paper again.

        The other way round from `propose_config`: the paths are given and the
        model may only say what each one is called, which block of the page it
        sits in and what it reads there. Proposing a fresh configuration and
        keeping whatever happened to line up recovers nothing at all when the
        second run names its fields differently, and on a long certificate it
        usually does.

        A path the model does not recognise on the paper is left out rather
        than guessed: a wrong label on a figure is worse than no label, since
        it is indistinguishable from a curated one.
        """
        ...
