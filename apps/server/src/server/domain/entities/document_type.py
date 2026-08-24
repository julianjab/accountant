from dataclasses import dataclass
from datetime import datetime
from typing import Any


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
