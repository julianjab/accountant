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
from server.reconciliation.core.contribution import (
    ContributionStatus,
    DocumentContribution,
    GatheredFacts,
)
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

    def facts_for(self, client_id: str, period: Period, kind_id: str) -> GatheredFacts:
        kind = self._registry.get(kind_id)
        client = self._clients.get(client_id)
        subject = TaxId.parse(client.tax_id) if client is not None else None
        parsed_sources = tuple(
            source
            for source in kind.sources()
            if source.extractor is not None and source.role is FactRole.SPINE
        )

        facts: list[FinancialFact] = []
        contributions: list[DocumentContribution] = []

        for document in self._documents.list_by_client(client_id):
            # A format this kind parses itself is tried whatever intake made of
            # it. Intake classifies against the configured document types, and
            # the exogena report is not one of them — it has a parser here
            # instead of an extraction prompt — so intake marks it FAILED. That
            # verdict is about OCR, not about this file, and honouring it would
            # discard the very document the reconciliation is built around.
            parsed, parse_status = self._from_parser(document, parsed_sources, subject)
            if parsed is not None:
                facts.extend(parsed)
                contributions.append(
                    _contribution(document, ContributionStatus.SPINE_PARSED, len(parsed))
                )
                continue

            if document.status not in _USABLE:
                contributions.append(
                    _contribution(
                        document,
                        ContributionStatus.NOT_READY,
                        detail=document.error or str(document.status),
                    )
                )
                continue

            projected, status, detail = self._from_extraction(document, kind_id, subject, period)
            facts.extend(projected)
            # A parser that could not read the bytes is only the answer when
            # nothing else explains the silence. The same document may well
            # have usable extracted data already stored, and reporting it as
            # unreadable would hide facts that are right there.
            if not projected and parse_status is not None:
                status, detail = parse_status, ""
            contributions.append(_contribution(document, status, len(projected), detail))

        return GatheredFacts(facts=tuple(facts), contributions=tuple(contributions))

    def _from_parser(
        self,
        document,
        sources: tuple[FactSourceSpec, ...],
        subject: TaxId | None,
    ) -> tuple[tuple[FinancialFact, ...] | None, ContributionStatus | None]:
        """Run a kind's own parser when the document's format is one it owns.

        A failed read is remembered rather than returned outright: another
        source may still recognise the file, and the caller may have stored
        extraction for it already.
        """
        unreadable = False
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
                unreadable = True
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
                ), None
            except SourceNotRecognized:
                # A spreadsheet that is not this kind's report. Ordinary — the
                # client's folder holds all sorts of files.
                logger.debug(
                    "Document is not a %s source", source.id, extra={"document_id": document.id}
                )
                continue
        return None, ContributionStatus.UNREADABLE if unreadable else None

    def _from_extraction(
        self, document, kind_id: str, subject: TaxId | None, period: Period
    ) -> tuple[tuple[FinancialFact, ...], ContributionStatus, str]:
        """Project OCR output through the document type's concept mapping.

        Returns why nothing came out as well as what did. Every one of these
        outcomes used to be a silent zero: the document showed as processed,
        the claim it was meant to satisfy showed as missing, and nothing
        connected the two.
        """
        if document.document_type_id is None:
            return (), ContributionStatus.NOT_CLASSIFIED, ""

        mapping = self._mappings.get(document.document_type_id, kind_id)
        if mapping is None:
            return (), ContributionStatus.TYPE_NOT_MAPPED, ""

        extracted = self._extracted_data.get_by_document(document.id)
        if extracted is None:
            return (), ContributionStatus.NO_EXTRACTION, ""

        document_type = self._document_types.get(document.document_type_id)
        if (
            document_type is not None
            and document_type.tax_years
            and period.year not in document_type.tax_years
        ):
            # A type tagged for other years is not a match for this one. Issuers
            # change their certificate between years, and two configurations of
            # the same paperwork must not read each other's documents.
            return (
                (),
                ContributionStatus.OTHER_PERIOD,
                ", ".join(str(year) for year in sorted(document_type.tax_years)),
            )
        try:
            projected = project_facts(
                mapping,
                extracted.fields,
                source_id=document.id,
                period=period,
                subject_tax_id=subject,
                reporter_name=document_type.name if document_type is not None else "",
                locator=document.file_name,
            )
        except ValueError:
            # The mapping's reporter field held nothing that reads as a tax id
            # — often the party's *name* rather than its number. Every fact
            # would be unattributable, so none is produced.
            logger.warning(
                "Could not attribute a document to a reporting party",
                extra={"document_id": document.id, "reporter_path": mapping.reporter_path},
            )
            return (
                (),
                ContributionStatus.NO_REPORTING_PARTY,
                mapping.reporter_path or "",
            )

        if not projected:
            return (), ContributionStatus.NO_AMOUNTS, ""

        # Facts exist but for another year: the certificate is real and simply
        # does not belong to the period being reconciled. Saying so beats
        # leaving the claim unexplained.
        in_period = tuple(fact for fact in projected if fact.period == period)
        if not in_period:
            # A document can state more than one period; naming only the first
            # would misreport which years it actually covers.
            years = sorted({fact.period.key for fact in projected})
            return (), ContributionStatus.OTHER_PERIOD, ", ".join(years)

        return in_period, ContributionStatus.CONTRIBUTED, ""


def _contribution(
    document, status: ContributionStatus, fact_count: int = 0, detail: str = ""
) -> DocumentContribution:
    return DocumentContribution(
        document_id=document.id,
        file_name=document.file_name,
        status=status,
        fact_count=fact_count,
        detail=detail,
    )
