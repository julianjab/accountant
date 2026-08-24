"""Turns a client's documents into the facts a reconciliation runs on.

This is the composition edge: the only module allowed to know both intake and
reconciliation. Keeping it here — rather than letting the engine reach for a
document repository — is what lets a second reconciliation model reuse all of
intake without either side importing the other.
"""

from __future__ import annotations

import logging

from server.domain.entities import DocumentStatus
from server.domain.ports import (
    ClientRepository,
    DocumentRepository,
    DocumentStorage,
    DocumentTypeRepository,
    ExtractedDataRepository,
)
from server.reconciliation.application.ports import ConceptMappingRepository
from server.reconciliation.core.kind import (
    FactSourceSpec,
    SourceContent,
    SourceNotRecognized,
)
from server.reconciliation.core.projection import project_facts
from server.reconciliation.core.registry import KindRegistry
from server.shared import FactRole, FinancialFact, Period, TaxId

logger = logging.getLogger(__name__)

# A document still being classified or extracted has nothing to contribute, and
# a failed one has nothing trustworthy to contribute.
_USABLE = (DocumentStatus.PROCESSED, DocumentStatus.APPROVED)


class DocumentFactProvider:
    """Implements `reconciliation.application.ports.FactProvider`."""

    def __init__(
        self,
        registry: KindRegistry,
        clients: ClientRepository,
        documents: DocumentRepository,
        document_types: DocumentTypeRepository,
        extracted_data: ExtractedDataRepository,
        mappings: ConceptMappingRepository,
        storage: DocumentStorage,
    ) -> None:
        self._registry = registry
        self._clients = clients
        self._documents = documents
        self._document_types = document_types
        self._extracted_data = extracted_data
        self._mappings = mappings
        self._storage = storage

    def facts_for(self, client_id: str, period: Period, kind_id: str) -> tuple[FinancialFact, ...]:
        kind = self._registry.get(kind_id)
        client = self._clients.get(client_id)
        subject = TaxId.parse(client.tax_id) if client is not None else None
        parsed_sources = tuple(
            source
            for source in kind.sources()
            if source.extractor is not None and source.role is FactRole.SPINE
        )

        facts: list[FinancialFact] = []
        for document in self._documents.list_by_client(client_id):
            # A format this kind parses itself is tried whatever intake made of
            # it. Intake classifies against the configured document types, and
            # the exogena report is not one of them — it has a parser here
            # instead of an extraction prompt — so intake marks it FAILED. That
            # verdict is about OCR, not about this file, and honouring it would
            # discard the very document the reconciliation is built around.
            extracted = self._from_parser(document, parsed_sources, subject)
            if extracted is None:
                if document.status not in _USABLE:
                    continue
                extracted = self._from_extraction(document, kind_id, subject, period)
            facts.extend(extracted or ())
        return tuple(facts)

    def _from_parser(
        self,
        document,
        sources: tuple[FactSourceSpec, ...],
        subject: TaxId | None,
    ) -> tuple[FinancialFact, ...] | None:
        """Run a kind's own parser when the document's format is one it owns."""
        for source in sources:
            if document.mime_type not in source.media_types:
                continue
            try:
                content = self._storage.download(document.drive_file_id)
            except Exception:
                # Parsers are now tried whatever intake made of the document,
                # and a FAILED one often got there because the file was
                # unreadable, moved or deleted. One unreachable file must not
                # take the whole reconciliation down with it.
                logger.warning(
                    "Could not read a document the kind parses itself",
                    extra={"document_id": document.id, "source_id": source.id},
                )
                continue
            try:
                return source.extractor.extract(
                    SourceContent(
                        data=content.data,
                        media_type=content.mime_type,
                        file_name=content.file_name,
                        source_id=document.id,
                        subject_tax_id=subject,
                        # The report states its own period; the requested one is
                        # only a fallback. A client's folder holds several years
                        # and the file, not the caller, is the authority on which
                        # year it covers.
                        period=None,
                    )
                )
            except SourceNotRecognized:
                # A spreadsheet that is not this kind's report. Ordinary — the
                # client's folder holds all sorts of files.
                logger.debug(
                    "Document is not a %s source", source.id, extra={"document_id": document.id}
                )
                continue
        return None

    def _from_extraction(
        self, document, kind_id: str, subject: TaxId | None, period: Period
    ) -> tuple[FinancialFact, ...]:
        """Project OCR output through the document type's concept mapping."""
        if document.document_type_id is None:
            return ()
        mapping = self._mappings.get(document.document_type_id, kind_id)
        if mapping is None:
            # The type has not been mapped onto this kind's vocabulary yet.
            # Silence here is correct: the document still shows in intake, and
            # the reconciliation reports the gap it leaves as missing evidence
            # rather than inventing facts for it.
            return ()
        extracted = self._extracted_data.get_by_document(document.id)
        if extracted is None:
            return ()

        document_type = self._document_types.get(document.document_type_id)
        try:
            return project_facts(
                mapping,
                extracted.fields,
                source_id=document.id,
                period=period,
                subject_tax_id=subject,
                reporter_name=document_type.name if document_type is not None else "",
                locator=document.file_name,
            )
        except ValueError:
            # No reporting party could be determined, so these amounts cannot
            # be attributed to anyone. Dropping them keeps the report honest:
            # the claims they would have backed stay MISSING_EVIDENCE.
            logger.warning(
                "Could not project document into facts",
                extra={"document_id": document.id, "document_type_id": document.document_type_id},
            )
            return ()
