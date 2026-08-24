from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class FieldRole(StrEnum):
    """What a field of a document holds.

    Kept so a screen can offer the few fields that matter — the identifier
    that ties the paper to a party, and the figures — instead of twenty rows
    the reader has to triage themselves.
    """

    #: A tax number, account number or document number.
    IDENTIFIER = "identifier"
    #: A monetary figure.
    AMOUNT = "amount"
    #: A date, a name, an address, a notice.
    CONTEXT = "context"


@dataclass(frozen=True, slots=True)
class DocumentTypeField:
    """One field this type extracts, described the way the document does.

    Stored rather than derived: the schema knows a field's path and its JSON
    type, and neither tells a reader what the paper calls it or which block of
    the page it came from. Without that, every screen showing extracted data is
    back to rendering dotted paths.
    """

    path: str
    label: str
    role: FieldRole = FieldRole.CONTEXT
    #: The block of the document this field sits in, named as the document
    #: names it, so a screen can be laid out like the page.
    section: str = ""


@dataclass(frozen=True, slots=True)
class DocumentType:
    """Config entity: how a document kind is recognized and extracted.

    Example: "Bancolombia statement".
    """

    id: str
    name: str
    description: str
    extraction_prompt: str
    extraction_schema: dict[str, Any]
    active: bool
    created_at: datetime
    #: Tax years this type applies to. Empty means any year — the common case.
    #: Set it when an issuer changes its certificate between years and the same
    #: paperwork needs two configurations that must not be mixed.
    tax_years: tuple[int, ...] = ()
    #: The document this type was configured from, so whoever revisits the
    #: configuration can read the paper it was derived from.
    sample_document_id: str | None = None
    #: What each extracted field is called and where it sits on the page.
    fields: tuple[DocumentTypeField, ...] = field(default_factory=tuple)
