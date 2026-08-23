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
