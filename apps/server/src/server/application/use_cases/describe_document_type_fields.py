from dataclasses import dataclass

from server.application.use_cases.update_document_type import DocumentTypeNotFound
from server.domain.extraction_schema import list_schema_paths
from server.domain.ports import (
    DocumentContent,
    DocumentTypeConfigurator,
    DocumentTypeRepository,
    ProposedField,
)


@dataclass(frozen=True, slots=True)
class DescribeDocumentTypeFieldsInput:
    document_type_id: str
    document: DocumentContent


class DescribeDocumentTypeFields:
    """Reads a paper again to say what a type's existing fields are called.

    A type configured before descriptions were stored — or one whose proposal
    came back with none — shows a column of dotted paths that nothing offers to
    fill. The obvious repair, proposing a configuration from the same sample
    again, recovers only the paths the second run happens to name identically,
    which on a long certificate is routinely none of them.

    So the schema is the question rather than the answer: its own paths are
    handed to the model, which may only describe them. Nothing is written here
    — the caller decides how the descriptions meet the ones it already curated.
    """

    def __init__(
        self,
        document_types: DocumentTypeRepository,
        configurator: DocumentTypeConfigurator,
    ) -> None:
        self._document_types = document_types
        self._configurator = configurator

    def execute(self, data: DescribeDocumentTypeFieldsInput) -> tuple[ProposedField, ...]:
        document_type = self._document_types.get(data.document_type_id)
        if document_type is None:
            raise DocumentTypeNotFound(f"Document type {data.document_type_id} not found")
        paths = list_schema_paths(document_type.extraction_schema)
        return self._configurator.describe_fields(data.document, document_type.name, paths)
