import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, HttpUrl, TypeAdapter, field_validator, model_validator

from server.domain.entities import DocumentStatus
from server.shared import TaxId

_HTTPS_URL = TypeAdapter(HttpUrl)
_YEAR = re.compile(r"\b(19|20)\d{2}\b")


def _validate_declared_tax_id(value: str | None) -> str | None:
    """A declared reporting party has to be a number, not a name.

    Checked at the edge so it comes back as the caller's mistake, which they
    can fix. Left to the projection it resolves to nothing, the mapping falls
    back to whoever the caller supplied, and the type reads as configured
    while attributing its figures to somebody else.
    """
    if value is None or not value.strip():
        return None
    if TaxId.parse(value) is None:
        raise ValueError(
            f"{value!r} is not a tax id: give the NUMBER the party reports under, not its name"
        )
    return value


def _validate_declared_period(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    if _YEAR.search(value) is None:
        raise ValueError(f"{value!r} does not contain a year")
    return value


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


class DocumentTypeFieldPayload(BaseModel):
    """One extracted field, described the way the document describes it.

    Carried on the type rather than recomputed per screen: the schema knows a
    path and a JSON type, neither of which tells a reader what the paper calls
    the field or which block of the page it sits in.
    """

    path: str
    label: str
    #: identifier | amount | context.
    role: str = "context"
    #: The block of the document this field belongs to. Empty when unknown.
    section: str = ""
    #: What the field said on the sample this type was configured from. Empty
    #: when unknown, which is every type saved before it was carried.
    sample_value: str = ""


class DocumentTypeResponse(BaseModel):
    id: str
    name: str
    description: str
    extraction_prompt: str
    extraction_schema: dict[str, Any]
    active: bool
    created_at: datetime
    #: Empty means the type applies to any tax year.
    tax_years: list[int] = []
    sample_document_id: str | None = None
    #: What each field is and where it sits, so the configurator and the
    #: document detail can lay themselves out like the document.
    fields: list[DocumentTypeFieldPayload] = []


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
    #: Set when the file was read by a dedicated parser instead of OCR, which
    #: is why such a document has no `document_type_id`.
    source_id: str | None = None


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


class DocumentContributionResponse(BaseModel):
    """What one document contributed to the reconciliation, and why."""

    document_id: str
    file_name: str
    status: str
    fact_count: int
    detail: str


class ReconciliationReportResponse(BaseModel):
    id: str
    client_id: str
    kind_id: str
    period: str
    generated_at: datetime
    summary: ReconciliationSummaryResponse
    findings: list[ReconciliationFindingResponse]
    contributions: list[DocumentContributionResponse]


class ConceptMappingEntryPayload(BaseModel):
    field_path: str
    concept_id: str
    account_path: str | None = None
    sign: int = 1
    #: Which claim of the exogena this field answers. Null means the field is
    #: extracted but never compared against anything.
    spine_concept_id: str | None = None
    #: Compare account by account instead of totalling per reporting party.
    per_account: bool = False

    @field_validator("sign")
    @classmethod
    def _check_sign(cls, value: int) -> int:
        if value not in (1, -1):
            raise ValueError("sign must be 1 or -1")
        return value

    @model_validator(mode="after")
    def _account_comparison_needs_an_account(self) -> "ConceptMappingEntryPayload":
        # Rejected here so the caller gets a 422 naming the field. The entity
        # refuses this too, but that far in it is a 500 — an error the caller
        # cannot act on for a mistake they can fix.
        if self.per_account and not self.account_path:
            raise ValueError("per_account requires account_path")
        return self


class ConceptMappingRequest(BaseModel):
    entries: list[ConceptMappingEntryPayload]
    reporter_path: str | None = None
    reporter_name_path: str | None = None
    period_path: str | None = None
    #: Who reports, when the document never prints its own issuer. What the
    #: document says always wins; this only fills a silence.
    reporter_tax_id: str | None = None
    reporter_name: str | None = None
    #: The period every document of this type covers, when the paper omits it.
    period: str | None = None

    _check_reporter_tax_id = field_validator("reporter_tax_id")(_validate_declared_tax_id)
    _check_period = field_validator("period")(_validate_declared_period)


class ConceptMappingResponse(BaseModel):
    document_type_id: str
    kind_id: str
    entries: list[ConceptMappingEntryPayload]
    reporter_path: str | None
    reporter_name_path: str | None
    period_path: str | None
    reporter_tax_id: str | None = None
    reporter_name: str | None = None
    period: str | None = None


class DocumentTypeCreateRequest(BaseModel):
    """The configuration a person approved, saved as reviewed.

    The proposal is not re-requested here: two runs of the model over one
    document do not agree field for field, so asking again would store
    something other than what was on screen when they said yes.
    """

    name: str
    description: str
    extraction_prompt: str
    #: Already trimmed to the fields that were kept.
    extraction_schema: dict[str, Any]
    field_mappings: list[ConceptMappingEntryPayload] = []
    reporter_path: str | None = None
    reporter_name_path: str | None = None
    period_path: str | None = None
    #: Who reports, when the document never prints its own issuer. What the
    #: document says always wins; this only fills a silence.
    reporter_tax_id: str | None = None
    reporter_name: str | None = None
    #: The period every document of this type covers, when the paper omits it.
    period: str | None = None
    tax_years: list[int] = []
    kind_id: str | None = None
    #: The document the configuration was derived from, when it came from one
    #: already in the client's folder.
    sample_document_id: str | None = None
    #: The fields that were kept, with the label and section the proposal gave
    #: them. Empty is allowed and means no screen can do better than paths.
    fields: list[DocumentTypeFieldPayload] = []

    _check_reporter_tax_id = field_validator("reporter_tax_id")(_validate_declared_tax_id)
    _check_period = field_validator("period")(_validate_declared_period)


class DocumentTypeUpdateRequest(BaseModel):
    """A partial edit; an omitted field keeps its stored value.

    Every field is optional because the common edit is a single one — trimming
    the schema down to the fields the accountant actually needs — and a client
    that had to resend the whole type would overwrite whatever it read stale.
    """

    name: str | None = None
    description: str | None = None
    active: bool | None = None
    #: An empty list means "applies to any year" and is a real choice, so it
    #: cannot be spelled the same way as "leave this alone".
    tax_years: list[int] | None = None
    extraction_prompt: str | None = None
    extraction_schema: dict[str, Any] | None = None
    #: Omitted keeps the stored descriptions; sent replaces them wholesale,
    #: since an edit that trims the schema is exactly when they change.
    fields: list[DocumentTypeFieldPayload] | None = None
    #: The document the configuration is derived from. Settable after the fact
    #: so a type configured before samples were recorded can be pointed at the
    #: paper it came from instead of staying permanently uncheckable.
    sample_document_id: str | None = None


class MappingChangeResponse(BaseModel):
    """One consequence an edited schema had on a stored concept mapping."""

    kind_id: str | None
    change: str
    #: The path in the old mapping that the new schema no longer declares.
    path: str | None
    field_path: str | None
    concept_id: str | None
    reason: str


class DocumentTypeUpdatedResponse(DocumentTypeResponse):
    """The saved type, plus what editing its schema cost its concept mappings.

    A subclass so anything already reading a document type keeps its shape.
    """

    #: Empty when the edit left the extraction schema alone.
    mapping_changes: list[MappingChangeResponse]


class ClientDocumentsImportResponse(BaseModel):
    """What one folder import did, split so the caller can act on each part."""

    imported: list[DocumentResponse]
    failed: list[DocumentResponse]
    skipped: int
    #: Files with no readable bytes, so no document exists for them at all.
    unreadable: list[str]


class ProposedFieldMappingResponse(BaseModel):
    field_path: str
    concept_id: str
    account_path: str | None
    sign: int


class UnmappedFieldResponse(BaseModel):
    field_path: str
    reason: str


class ProposedFieldResponse(BaseModel):
    """One field the AI found, with enough for a person to judge it without
    the document open beside them."""

    path: str
    label: str
    #: identifier · amount · context
    role: str
    sample_value: str
    #: The block of the document this field came from, so a selection screen
    #: can be laid out the way the paper is.
    section: str


class DocumentTypeFieldDescriptionsResponse(BaseModel):
    """What a re-reading of a sample says about the fields a type already has.

    Only descriptions: the prompt, the schema and the mappings are what someone
    curated, and this reads a paper to fill in labels, blocks and sample values
    without reopening any of those decisions.
    """

    fields: list[ProposedFieldResponse]


class DocumentTypeProposalResponse(BaseModel):
    """What the AI would configure, stored nowhere until someone approves it."""

    extraction_prompt: str
    extraction_schema: dict[str, Any]
    fields: list[ProposedFieldResponse]
    field_mappings: list["ProposedFieldMappingResponse"]
    unmapped_fields: list["UnmappedFieldResponse"]
    kind_id: str | None
    reporter_path: str | None
    reporter_name_path: str | None
    period_path: str | None


class DocumentTypeCreatedResponse(DocumentTypeResponse):
    """What defining a type produced, including how its fields were mapped.

    A subclass so the list endpoints and any existing client keep the shape
    they already read; the mapping is additive.
    """

    kind_id: str | None
    field_mappings: list[ProposedFieldMappingResponse]
    #: Extracted but not reconcilable, with the AI's reason for leaving them
    #: out. Returned so the gap is a visible decision, not a silent omission.
    unmapped_fields: list[UnmappedFieldResponse]
