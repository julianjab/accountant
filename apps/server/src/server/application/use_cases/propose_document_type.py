from collections.abc import Sequence
from dataclasses import dataclass

from server.domain.ports import (
    ConceptOption,
    DocumentContent,
    DocumentTypeConfigurator,
    ProposedOcrConfig,
)


@dataclass(frozen=True, slots=True)
class ProposeDocumentTypeInput:
    type_name: str
    sample_document: DocumentContent
    concepts: Sequence[ConceptOption] = ()


class ProposeDocumentType:
    """Asks the AI what a sample document holds, and stores nothing.

    Split from saving on purpose. A proposal routinely lists twenty fields
    where the accountant wants the identifier and three figures, and saving it
    whole made the type theirs to prune afterwards rather than theirs to choose
    up front. Nothing is written until a person has said which fields matter.
    """

    def __init__(self, configurator: DocumentTypeConfigurator) -> None:
        self._configurator = configurator

    def execute(self, data: ProposeDocumentTypeInput) -> ProposedOcrConfig:
        return self._configurator.propose_config(
            data.sample_document, data.type_name, data.concepts
        )
