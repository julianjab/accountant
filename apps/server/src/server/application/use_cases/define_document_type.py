import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from server.domain.entities import DocumentType
from server.domain.ports import (
    ConceptOption,
    DocumentContent,
    DocumentTypeConfigurator,
    DocumentTypeRepository,
    ProposedFieldMapping,
)


@dataclass(frozen=True, slots=True)
class DefineDocumentTypeInput:
    name: str
    description: str
    sample_document: DocumentContent
    #: The vocabulary extracted fields may be mapped onto. Empty means the
    #: caller wants extraction only, with no reconciliation behind it.
    concepts: Sequence[ConceptOption] = ()
    #: Tax years this type applies to. Empty means any year.
    tax_years: tuple[int, ...] = ()
    #: The document the configuration was derived from, kept so whoever
    #: revisits it can read the paper behind the choices.
    sample_document_id: str | None = None


@dataclass(frozen=True, slots=True)
class DefinedDocumentType:
    """The saved type, plus what the AI said about mapping its fields.

    The mapping travels beside the type rather than on it: which concepts a
    field means is a reconciliation concern, and DocumentType belongs to
    intake, which must not know reconciliation exists. The caller stores it
    wherever that context keeps it.
    """

    document_type: DocumentType
    field_mappings: tuple[ProposedFieldMapping, ...]
    #: Fields that will be extracted but cannot be reconciled, with the AI's
    #: reason. Returned so the gap is visible rather than silently absent.
    unmapped_fields: tuple[tuple[str, str], ...]
    #: Where the document names the party reporting these amounts, and the
    #: period it covers. Without the first, no fact can be attributed to
    #: anyone and every mapping above is discarded.
    reporter_path: str | None = None
    reporter_name_path: str | None = None
    period_path: str | None = None


class DefineDocumentType:
    """Config > Document type: an AI inspects a sample document and proposes the
    extraction prompt + schema for that type (e.g. "Bancolombia statement")."""

    def __init__(
        self,
        configurator: DocumentTypeConfigurator,
        document_types: DocumentTypeRepository,
    ) -> None:
        self._configurator = configurator
        self._document_types = document_types

    def execute(self, data: DefineDocumentTypeInput) -> DefinedDocumentType:
        proposal = self._configurator.propose_config(data.sample_document, data.name, data.concepts)
        document_type = DocumentType(
            id=str(uuid.uuid4()),
            name=data.name,
            description=data.description,
            extraction_prompt=proposal.extraction_prompt,
            extraction_schema=proposal.extraction_schema,
            active=True,
            created_at=datetime.now(UTC),
            tax_years=data.tax_years,
            sample_document_id=data.sample_document_id,
        )
        self._document_types.save(document_type)
        return DefinedDocumentType(
            document_type=document_type,
            field_mappings=proposal.field_mappings,
            unmapped_fields=proposal.unmapped_fields,
            reporter_path=proposal.reporter_path,
            reporter_name_path=proposal.reporter_name_path,
            period_path=proposal.period_path,
        )
