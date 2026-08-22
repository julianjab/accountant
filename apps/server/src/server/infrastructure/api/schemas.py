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
