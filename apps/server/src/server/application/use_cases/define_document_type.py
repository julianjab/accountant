import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from server.domain.entities import DocumentType, DocumentTypeField
from server.domain.ports import (
    ConceptOption,
    DocumentContent,
    DocumentTypeConfigurator,
    DocumentTypeRepository,
    ProposedFieldMapping,
    ProposedOcrConfig,
)


@dataclass(frozen=True, slots=True)
class DefineDocumentTypeInput:
    name: str
    description: str
    #: The configuration a person approved. Supplied together, these are saved
    #: as they are and no AI call is made — asking again would store something
    #: other than what was reviewed, since two runs over one document do not
    #: agree field for field.
    extraction_prompt: str | None = None
    extraction_schema: dict[str, Any] | None = None
    field_mappings: tuple[ProposedFieldMapping, ...] = ()
    reporter_path: str | None = None
    reporter_name_path: str | None = None
    period_path: str | None = None
    #: Only needed when no approved configuration is given, in which case this
    #: proposes one and saves it unreviewed.
    sample_document: DocumentContent | None = None
    #: The vocabulary extracted fields may be mapped onto. Empty means the
    #: caller wants extraction only, with no reconciliation behind it.
    concepts: Sequence[ConceptOption] = ()
    #: Tax years this type applies to. Empty means any year.
    tax_years: tuple[int, ...] = ()
    #: The document the configuration was derived from, kept so whoever
    #: revisits it can read the paper behind the choices.
    sample_document_id: str | None = None
    #: What the fields are called and which block of the document they came
    #: from. Saved with the type because a schema records a path and a JSON
    #: type, and no screen can name a field from those.
    fields: tuple[DocumentTypeField, ...] = ()
    #: Everything the reading identified, of which `extraction_schema` is the
    #: ticked subset. Stored so a field left out can be ticked back later
    #: without paying for a second reading of the same paper.
    candidate_schema: dict[str, Any] | None = None


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

    @staticmethod
    def _approved(data: DefineDocumentTypeInput) -> ProposedOcrConfig | None:
        """What the caller reviewed, when they reviewed anything."""
        if data.extraction_prompt is None or data.extraction_schema is None:
            return None
        return ProposedOcrConfig(
            extraction_prompt=data.extraction_prompt,
            extraction_schema=data.extraction_schema,
            field_mappings=data.field_mappings,
            reporter_path=data.reporter_path,
            reporter_name_path=data.reporter_name_path,
            period_path=data.period_path,
        )

    def _propose(self, data: DefineDocumentTypeInput) -> ProposedOcrConfig:
        if data.sample_document is None:
            raise ValueError(
                "Defining a document type needs either an approved configuration "
                "or a sample document to propose one from"
            )
        return self._configurator.propose_config(data.sample_document, data.name, data.concepts)

    def execute(self, data: DefineDocumentTypeInput) -> DefinedDocumentType:
        proposal = self._approved(data) or self._propose(data)
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
            fields=data.fields,
            candidate_schema=data.candidate_schema,
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
