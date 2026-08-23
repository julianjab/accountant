from datetime import datetime
from typing import Any

from pydantic import BaseModel, HttpUrl, TypeAdapter, field_validator

from server.domain.entities import DocumentStatus

_HTTPS_URL = TypeAdapter(HttpUrl)


def _validate_https_url(value: str | None) -> str | None:
    if value is None:
        return None
    url = _HTTPS_URL.validate_python(value)
    if url.scheme != "https":
        raise ValueError("spreadsheet_url must use https")
    return str(url)


class ClientCreateRequest(BaseModel):
    name: str
    tax_id: str | None = None
    email: str | None = None
    drive_folder_url: str | None = None
    spreadsheet_url: str | None = None

    @field_validator("drive_folder_url")
    @classmethod
    def _drive_folder_url_must_be_https(cls, value: str | None) -> str | None:
        # Rendered as a plain <a href> on the client detail page — reject
        # anything other than an https URL so a value like `javascript:...`
        # can never end up executable there.
        if value is not None and not value.startswith("https://"):
            msg = "drive_folder_url must be an https URL"
            raise ValueError(msg)
        return value

    _validate_spreadsheet_url = field_validator("spreadsheet_url")(_validate_https_url)


class ClientResponse(BaseModel):
    id: str
    name: str
    tax_id: str | None
    email: str | None
    created_at: datetime
    drive_folder_id: str | None = None
    drive_folder_url: str | None = None
    spreadsheet_url: str | None = None


class ClientImportResponse(BaseModel):
    created: list[ClientResponse]
    renamed: list[ClientResponse]
    unchanged: int


class DocumentTypeResponse(BaseModel):
    id: str
    name: str
    description: str
    extraction_prompt: str
    extraction_schema: dict[str, Any]
    active: bool
    created_at: datetime


class DocumentResponse(BaseModel):
    id: str
    client_id: str
    document_type_id: str | None
    drive_file_id: str
    file_name: str
    mime_type: str
    status: DocumentStatus
    error: str | None
    created_at: datetime
    processed_at: datetime | None
    reviewed_at: datetime | None
    approved_by: str | None


class DocumentApproveRequest(BaseModel):
    approved_by: str | None = None


class DocumentMetricsResponse(BaseModel):
    """Dashboard figures. "Today" is computed in UTC.

    `avg_processing_seconds` is the mean of (processed_at - created_at) over
    documents with status in {processed, approved} (approval never reverses
    the OCR pipeline); `null` when there is no such document yet.
    """

    unprocessed: int
    processed_today: int
    failed: int
    avg_processing_seconds: float | None


class ExtractedDataResponse(BaseModel):
    id: str
    document_id: str
    fields: dict[str, Any]
    confidence: float | None
    created_at: datetime


class SheetRowResponse(BaseModel):
    source_document_id: str
    source_document_file_name: str
    date: str
    description: str
    amount: str
    tax: str


class DriveWatchChannelResponse(BaseModel):
    id: str
    resource_id: str
    folder_id: str
    client_id: str
    expires_at: datetime


class GoogleUserResponse(BaseModel):
    email: str
    name: str
    picture: str | None


class ReconciliationConceptResponse(BaseModel):
    id: str
    label: str
    role: str
    description: str


class ReconciliationKindResponse(BaseModel):
    """What a client needs to render a reconciliation without knowing which
    model it is: the period granularity, and the vocabulary a document type's
    fields may be mapped onto."""

    id: str
    label: str
    period_granularity: str
    spine_concepts: list[ReconciliationConceptResponse]
    evidence_concepts: list[ReconciliationConceptResponse]


class ReconciliationFactResponse(BaseModel):
    source_id: str
    role: str
    reporter_tax_id: str
    reporter_name: str
    concept_id: str
    amount: str
    account: str | None
    detail: str
    locator: str


class ReconciliationFindingResponse(BaseModel):
    id: str
    status: str
    rule_id: str | None
    label: str
    reporter_tax_id: str
    reporter_name: str
    # Amounts travel as strings: the figures are exact decimals, and JSON
    # numbers are doubles in most clients. A cent lost in transport would show
    # up as a discrepancy the engine never found.
    spine_amount: str
    evidence_amount: str
    delta: str
    account: str | None
    account_match: str
    note: str
    spine_facts: list[ReconciliationFactResponse]
    evidence_facts: list[ReconciliationFactResponse]


class ReconciliationSummaryResponse(BaseModel):
    counts: dict[str, int]
    total_findings: int
    reconciled: int
    needing_attention: int


class ReconciliationReportResponse(BaseModel):
    id: str
    client_id: str
    kind_id: str
    period: str
    generated_at: datetime
    summary: ReconciliationSummaryResponse
    findings: list[ReconciliationFindingResponse]


class ConceptMappingEntryPayload(BaseModel):
    field_path: str
    concept_id: str
    account_path: str | None = None
    sign: int = 1

    @field_validator("sign")
    @classmethod
    def _check_sign(cls, value: int) -> int:
        if value not in (1, -1):
            raise ValueError("sign must be 1 or -1")
        return value


class ConceptMappingRequest(BaseModel):
    entries: list[ConceptMappingEntryPayload]
    reporter_path: str | None = None
    reporter_name_path: str | None = None
    period_path: str | None = None


class ConceptMappingResponse(BaseModel):
    document_type_id: str
    kind_id: str
    entries: list[ConceptMappingEntryPayload]
    reporter_path: str | None
    reporter_name_path: str | None
    period_path: str | None


class ClientDocumentsImportResponse(BaseModel):
    """What one folder import did, split so the caller can act on each part."""

    imported: list[DocumentResponse]
    failed: list[DocumentResponse]
    skipped: int
