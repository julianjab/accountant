"""The wiring: documents in intake become facts, and facts become a report."""

from __future__ import annotations

import io
from datetime import UTC, datetime

import fixtures
import pytest
from openpyxl import Workbook

from server.domain.entities import (
    Client,
    Document,
    DocumentStatus,
    DocumentType,
    ExtractedData,
)
from server.domain.ports import DocumentContent
from server.infrastructure.adapters.in_memory_repositories import (
    InMemoryClientRepository,
    InMemoryDocumentRepository,
    InMemoryDocumentTypeRepository,
    InMemoryExtractedDataRepository,
)
from server.reconciliation.application import ReconcileClientPeriod, ReconcileClientPeriodInput
from server.reconciliation.core.contribution import ContributionStatus
from server.reconciliation.core.findings import FindingStatus
from server.reconciliation.core.projection import ConceptMapping, ConceptMappingEntry
from server.reconciliation.core.registry import KindRegistry
from server.reconciliation.infrastructure import (
    DocumentFactProvider,
    InMemoryConceptMappingRepository,
    InMemoryReconciliationReportRepository,
)
from server.reconciliation.kinds.exogena import KIND_ID, ExogenaReconciliation
from server.shared import Period

NOW = datetime.now(UTC)
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class _Storage:
    """Stands in for Drive, keyed the way the provider addresses it.

    Anything not explicitly registered comes back as an unrelated spreadsheet,
    which is what a real client folder is full of.
    """

    def __init__(self, by_reference: dict[str, DocumentContent]) -> None:
        self._by_reference = by_reference

    def download(self, file_reference: str) -> DocumentContent:
        if file_reference in self._by_reference:
            return self._by_reference[file_reference]
        workbook = Workbook()
        workbook.active.append(["Fecha", "Concepto", "Débito"])
        buffer = io.BytesIO()
        workbook.save(buffer)
        return DocumentContent(data=buffer.getvalue(), mime_type=XLSX, file_name="otra.xlsx")


def _document(doc_id, mime_type, *, type_id=None, status=DocumentStatus.PROCESSED):
    return Document(
        id=doc_id,
        client_id="client-1",
        document_type_id=type_id,
        drive_file_id=f"drive-{doc_id}",
        file_name=f"{doc_id}.bin",
        mime_type=mime_type,
        status=status,
        error=None,
        created_at=NOW,
    )


def _document_type(type_id, name):
    return DocumentType(
        id=type_id,
        name=name,
        description=name,
        extraction_prompt="...",
        extraction_schema={"type": "object"},
        active=True,
        created_at=NOW,
    )


@pytest.fixture
def wiring():
    clients = InMemoryClientRepository()
    documents = InMemoryDocumentRepository()
    document_types = InMemoryDocumentTypeRepository()
    extracted = InMemoryExtractedDataRepository()
    mappings = InMemoryConceptMappingRepository()
    reports = InMemoryReconciliationReportRepository()

    clients.save(
        Client(
            id="client-1",
            name=fixtures.TAXPAYER_NAME,
            tax_id=fixtures.TAXPAYER_TAX_ID,
            email=None,
            created_at=NOW,
        )
    )
    document_types.save(
        _document_type(fixtures.BANCOLOMBIA_MAPPING.document_type_id, "Certificado Bancolombia")
    )
    documents.save(_document("exogena", XLSX))
    documents.save(
        _document(
            "cert-banco", "application/pdf", type_id=fixtures.BANCOLOMBIA_MAPPING.document_type_id
        )
    )
    extracted.save(
        ExtractedData(
            id="ex-1",
            document_id="cert-banco",
            fields=dict(fixtures.BANCOLOMBIA_CERTIFICATE_FIELDS),
            confidence=None,
            created_at=NOW,
        )
    )
    mappings.save(fixtures.BANCOLOMBIA_MAPPING)

    storage = _Storage(
        {
            "drive-exogena": DocumentContent(
                data=fixtures.exogena_workbook_bytes(),
                mime_type=XLSX,
                file_name="exogena-2025.xlsx",
            ),
            "drive-cert-banco": DocumentContent(
                data=b"%PDF-", mime_type="application/pdf", file_name="cert.pdf"
            ),
        }
    )
    registry = KindRegistry([ExogenaReconciliation()])
    provider = DocumentFactProvider(
        registry, clients, documents, document_types, extracted, mappings, storage
    )
    use_case = ReconcileClientPeriod(registry, provider, reports, mappings)
    return use_case, reports, documents, mappings, document_types, extracted


def test_reconciles_a_client_from_its_documents(wiring):
    use_case, reports, _, _, _, _ = wiring
    report = use_case.execute(ReconcileClientPeriodInput("client-1", KIND_ID, Period.of_year(2025)))
    assert report.summary.total_findings > 0
    assert reports.get_latest("client-1", KIND_ID, Period.of_year(2025)) == report

    bancolombia = [f for f in report.findings if f.reporter_tax_id.value == fixtures.BANCOLOMBIA]
    assert any(f.status.is_reconciled for f in bancolombia)


def test_documents_still_being_processed_contribute_nothing(wiring):
    """A half-extracted certificate must not partially satisfy a claim and
    turn a real gap into a false match."""
    use_case, _, documents, _, _, _ = wiring
    documents.save(
        _document(
            "cert-banco",
            "application/pdf",
            type_id=fixtures.BANCOLOMBIA_MAPPING.document_type_id,
            status=DocumentStatus.RUNNING_OCR,
        )
    )
    report = use_case.execute(ReconcileClientPeriodInput("client-1", KIND_ID, Period.of_year(2025)))
    assert all(not f.status.is_reconciled for f in report.findings)


def test_an_unmapped_document_type_leaves_the_claim_missing_rather_than_matched(wiring):
    use_case, _, _, mappings, _, _ = wiring
    mappings._by_key.clear()
    report = use_case.execute(ReconcileClientPeriodInput("client-1", KIND_ID, Period.of_year(2025)))
    assert FindingStatus.MISSING_EVIDENCE in {f.status for f in report.findings}
    assert all(not f.status.is_reconciled for f in report.findings)


def test_a_period_of_the_wrong_granularity_is_rejected(wiring):
    """The exogena is annual; a monthly request is a caller bug, not an empty
    report."""
    use_case, _, _, _, _, _ = wiring
    with pytest.raises(ValueError, match="reconciles by"):
        use_case.execute(ReconcileClientPeriodInput("client-1", KIND_ID, Period.of_month(2025, 3)))


def test_a_spreadsheet_that_is_not_an_exogena_is_passed_over(wiring):
    """The client's folder holds all sorts of files; one of them not being the
    report is ordinary, not a failure."""
    use_case, _, documents, _, _, _ = wiring
    documents.save(_document("otra-hoja", XLSX))
    report = use_case.execute(ReconcileClientPeriodInput("client-1", KIND_ID, Period.of_year(2025)))
    assert report.summary.total_findings > 0


def test_a_document_with_no_extracted_data_contributes_nothing(wiring):
    use_case, _, documents, _, _, _ = wiring
    documents.save(
        _document(
            "sin-ocr",
            "application/pdf",
            type_id=fixtures.BANCOLOMBIA_MAPPING.document_type_id,
        )
    )
    report = use_case.execute(ReconcileClientPeriodInput("client-1", KIND_ID, Period.of_year(2025)))
    assert report.summary.reconciled > 0


def test_a_document_that_was_never_classified_contributes_nothing(wiring):
    use_case, _, documents, _, _, _ = wiring
    documents.save(_document("sin-tipo", "application/pdf"))
    report = use_case.execute(ReconcileClientPeriodInput("client-1", KIND_ID, Period.of_year(2025)))
    assert report.summary.reconciled > 0


def test_an_unattributable_document_is_dropped_rather_than_guessed_at(wiring, caplog):
    """Facts nobody reported cannot back anyone's claim; the claims they would
    have satisfied must stay missing."""
    use_case, _, documents, mappings, document_types, extracted = wiring
    mappings.save(
        ConceptMapping(
            document_type_id="type-anonimo",
            kind_id=KIND_ID,
            reporter_path="no_existe",
            entries=(
                ConceptMappingEntry("saldo_cuenta_ahorros", "bank:cert_saldo_cuentas_ahorro"),
            ),
        )
    )
    document_types.save(_document_type("type-anonimo", "Certificado sin emisor"))
    documents.save(_document("anonimo", "application/pdf", type_id="type-anonimo"))
    extracted.save(
        ExtractedData(
            id="ex-anonimo",
            document_id="anonimo",
            fields={"saldo_cuenta_ahorros": "$ 999.00"},
            confidence=None,
            created_at=NOW,
        )
    )

    report = use_case.execute(ReconcileClientPeriodInput("client-1", KIND_ID, Period.of_year(2025)))
    assert all(f.reporter_tax_id.value for f in report.findings)


def test_reports_are_rebuilt_rather_than_accumulated(wiring):
    """A later document can turn five missing lines into one match, so a
    partially-updated report would drift from the documents it summarizes."""
    use_case, reports, _, _, _, _ = wiring
    request = ReconcileClientPeriodInput("client-1", KIND_ID, Period.of_year(2025))
    first = use_case.execute(request)
    second = use_case.execute(request)
    # A report is the current answer for a client and period, not an entry in
    # an event log: the rebuild replaces it rather than leaving an orphan
    # behind for every document that was ever uploaded.
    assert first.id == second.id
    assert reports.get_latest("client-1", KIND_ID, Period.of_year(2025)).id == second.id
    assert first.summary.counts == second.summary.counts


def test_a_client_with_no_reconciliation_yet_has_no_latest_report(wiring):
    _, reports, _, _, _, _ = wiring
    assert reports.get_latest("client-2", KIND_ID, Period.of_year(2025)) is None
    assert reports.get("nope") is None


def test_concept_mappings_are_stored_per_document_type_and_kind():
    repository = InMemoryConceptMappingRepository()
    mapping = ConceptMapping(
        document_type_id="t1",
        kind_id=KIND_ID,
        entries=(ConceptMappingEntry("saldo", "bank:cert_saldo_cuentas_ahorro"),),
    )
    repository.save(mapping)

    assert repository.get("t1", KIND_ID) == mapping
    # A type mapped for one kind is not mapped for another.
    assert repository.get("t1", "otro_modelo") is None
    assert repository.get("t2", KIND_ID) is None
    assert repository.list_for_kind(KIND_ID) == [mapping]
    assert repository.list_for_kind("otro_modelo") == []


def test_the_spine_is_parsed_even_though_intake_could_not_classify_it(wiring):
    """Intake classifies against the configured document types, and the exogena
    is not one of them — it has a parser here rather than an extraction prompt.
    Honouring intake's FAILED verdict would discard the document the whole
    reconciliation is built around."""
    use_case, _, documents, _, _, _ = wiring
    documents.save(_document("exogena", XLSX, status=DocumentStatus.FAILED))

    report = use_case.execute(ReconcileClientPeriodInput("client-1", KIND_ID, Period.of_year(2025)))

    assert report.summary.total_findings > 0
    assert any(f.spine_facts for f in report.findings)


def test_a_spine_whose_bytes_cannot_be_read_does_not_sink_the_run(wiring):
    """Parsers are tried whatever intake made of a document, and a FAILED one
    often got there because the file was unreadable, moved or deleted."""
    use_case, _, documents, _, _, _ = wiring

    class _Unreadable:
        def list_files(self, folder_reference):
            return []

        def download(self, file_reference):
            raise RuntimeError("410 gone")

    documents.save(_document("desaparecido", XLSX, status=DocumentStatus.FAILED))
    provider = _provider_of(use_case)
    provider._storage = _Unreadable()

    report = use_case.execute(ReconcileClientPeriodInput("client-1", KIND_ID, Period.of_year(2025)))
    assert report.summary.total_findings >= 0


def _provider_of(use_case):
    return use_case._facts


def test_every_document_says_what_it_contributed(wiring):
    """A processed document that fed the reconciliation nothing used to look
    exactly like one that worked: a green badge, and a claim reported as
    missing, with nothing connecting the two."""
    use_case, _, _, _, _, _ = wiring

    report = use_case.execute(ReconcileClientPeriodInput("client-1", KIND_ID, Period.of_year(2025)))

    by_file = {c.file_name: c for c in report.contributions}
    assert by_file["exogena.bin"].status is ContributionStatus.SPINE_PARSED
    assert by_file["exogena.bin"].fact_count > 0
    assert by_file["cert-banco.bin"].status is ContributionStatus.CONTRIBUTED


def test_a_document_whose_type_is_not_mapped_says_so(wiring):
    use_case, _, _, mappings, _, _ = wiring
    mappings._by_key.clear()

    report = use_case.execute(ReconcileClientPeriodInput("client-1", KIND_ID, Period.of_year(2025)))

    statuses = {c.file_name: c.status for c in report.contributions}
    assert statuses["cert-banco.bin"] is ContributionStatus.TYPE_NOT_MAPPED


def test_a_mapping_that_names_no_reporting_party_says_which_field_failed(wiring):
    """The real case: the AI pointed reporter_path at the fund's *name*, so
    every fact was unattributable and silently dropped."""
    use_case, _, _, mappings, _, _ = wiring
    mappings.save(
        ConceptMapping(
            document_type_id=fixtures.BANCOLOMBIA_MAPPING.document_type_id,
            kind_id=KIND_ID,
            reporter_path="agente_retenedor_nombre",
            entries=fixtures.BANCOLOMBIA_MAPPING.entries,
        )
    )

    report = use_case.execute(ReconcileClientPeriodInput("client-1", KIND_ID, Period.of_year(2025)))

    contribution = next(c for c in report.contributions if c.file_name == "cert-banco.bin")
    assert contribution.status is ContributionStatus.NO_REPORTING_PARTY
    assert contribution.detail == "agente_retenedor_nombre"


def test_a_certificate_for_another_year_says_which_year(wiring):
    """The real case: a 2024 certificate uploaded against a 2025
    reconciliation. Reporting the year beats leaving the claim unexplained."""
    use_case, _, _, mappings, _, extracted = wiring
    mappings.save(
        ConceptMapping(
            document_type_id=fixtures.BANCOLOMBIA_MAPPING.document_type_id,
            kind_id=KIND_ID,
            reporter_path=fixtures.BANCOLOMBIA_MAPPING.reporter_path,
            period_path="ano_gravable",
            entries=fixtures.BANCOLOMBIA_MAPPING.entries,
        )
    )
    extracted.save(
        ExtractedData(
            id="ex-2024",
            document_id="cert-banco",
            fields={**fixtures.BANCOLOMBIA_CERTIFICATE_FIELDS, "ano_gravable": "2024"},
            confidence=None,
            created_at=NOW,
        )
    )

    report = use_case.execute(ReconcileClientPeriodInput("client-1", KIND_ID, Period.of_year(2025)))

    contribution = next(c for c in report.contributions if c.file_name == "cert-banco.bin")
    assert contribution.status is ContributionStatus.OTHER_PERIOD
    assert contribution.detail == "2024"


def test_an_unreadable_spine_still_lets_its_extraction_be_used(wiring):
    """A transient Drive failure on a file the kind would parse must not throw
    away extraction already stored for that same document."""
    use_case, _, documents, _, _, _ = wiring
    documents.save(
        _document(
            "cert-banco",
            XLSX,
            type_id=fixtures.BANCOLOMBIA_MAPPING.document_type_id,
        )
    )
    provider = use_case._facts

    class _Unreadable:
        def list_files(self, folder_reference):
            return []

        def download(self, file_reference):
            raise RuntimeError("Drive is briefly unavailable")

    provider._storage = _Unreadable()

    report = use_case.execute(ReconcileClientPeriodInput("client-1", KIND_ID, Period.of_year(2025)))

    contribution = next(c for c in report.contributions if c.document_id == "cert-banco")
    assert contribution.status is ContributionStatus.CONTRIBUTED
    assert contribution.fact_count > 0


def test_what_the_user_configured_outranks_the_built_in_pack(wiring):
    """The point of making this editable: someone reading the certificate can
    overrule a default that does not fit their documents."""
    use_case, _, _, mappings, _, _ = wiring
    mappings.save(
        ConceptMapping(
            document_type_id=fixtures.BANCOLOMBIA_MAPPING.document_type_id,
            kind_id=KIND_ID,
            reporter_path=fixtures.BANCOLOMBIA_MAPPING.reporter_path,
            entries=(
                ConceptMappingEntry(
                    field_path="saldo_cuenta_ahorros",
                    concept_id="bank:cert_saldo_cuentas_ahorro",
                    spine_concept_id="dian:saldo-cuentas-bancarias",
                ),
            ),
        )
    )

    report = use_case.execute(ReconcileClientPeriodInput("client-1", KIND_ID, Period.of_year(2025)))

    matched = [f for f in report.findings if f.status.is_reconciled]
    assert any(f.rule_id == "configured.dian:saldo-cuentas-bancarias" for f in matched)
