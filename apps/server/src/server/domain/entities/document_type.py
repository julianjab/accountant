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
