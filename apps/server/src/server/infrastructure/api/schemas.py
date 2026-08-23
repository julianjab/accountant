from datetime import datetime
from typing import Any

from pydantic import BaseModel

from server.domain.entities import DocumentStatus


class ClientCreateRequest(BaseModel):
    name: str
    tax_id: str
    email: str | None = None


class ClientResponse(BaseModel):
    id: str
    name: str
    tax_id: str
    email: str | None
    created_at: datetime


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


class DriveWebhookPayload(BaseModel):
    client_id: str
    drive_file_id: str
    file_reference: str


class GoogleUserResponse(BaseModel):
    email: str
    name: str
    picture: str | None
