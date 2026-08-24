from collections.abc import Sequence
from dataclasses import dataclass

from server.application.use_cases.update_document_type import DocumentTypeNotFound
from server.domain.ports import (
    ConceptOption,
    DocumentContent,
    DocumentTypeConfigurator,
    DocumentTypeRepository,
    ExistingConfig,
    ProposedOcrConfig,
)


@dataclass(frozen=True, slots=True)
class ProposeDocumentTypeInput:
    type_name: str
    sample_document: DocumentContent
    concepts: Sequence[ConceptOption] = ()
    #: What the person configuring the type says the last reading got wrong.
    #: A table read as one row stays one row until someone says otherwise.
    guidance: str = ""
    #: The type being revised, when this is a regeneration rather than a first
    #: reading. Its current prompt and schema become the starting point.
    document_type_id: str | None = None


class ProposeDocumentType:
    """Asks the AI what a sample document holds, and stores nothing.

    Split from saving on purpose. A proposal routinely lists twenty fields
    where the accountant wants the identifier and three figures, and saving it
    whole made the type theirs to prune afterwards rather than theirs to choose
    up front. Nothing is written until a person has said which fields matter.
    """

    def __init__(
        self,
        configurator: DocumentTypeConfigurator,
        document_types: DocumentTypeRepository,
    ) -> None:
        self._configurator = configurator
        self._document_types = document_types

    def execute(self, data: ProposeDocumentTypeInput) -> ProposedOcrConfig:
        return self._configurator.propose_config(
            data.sample_document,
            data.type_name,
            data.concepts,
            guidance=data.guidance,
            base=self._base(data.document_type_id),
        )

    def _base(self, document_type_id: str | None) -> ExistingConfig | None:
        """The configuration being revised, when one was named.

        Read here rather than sent by the caller: the prompt and schema a
        revision must preserve are what the server stores, and a client that
        posted its own copy could revise a version of the type that no longer
        exists.
        """
        if document_type_id is None:
            return None
        document_type = self._document_types.get(document_type_id)
        if document_type is None:
            raise DocumentTypeNotFound(f"Document type {document_type_id} not found")
        return ExistingConfig(
            extraction_prompt=document_type.extraction_prompt,
            extraction_schema=document_type.extraction_schema,
        )
