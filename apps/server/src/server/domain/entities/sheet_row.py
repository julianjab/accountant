from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SheetRow:
    source_document_id: str
    source_document_file_name: str
    date: str
    description: str
    amount: str
    tax: str
