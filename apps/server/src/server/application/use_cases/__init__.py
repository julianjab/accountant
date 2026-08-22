from server.application.use_cases.define_document_type import (
    DefineDocumentType,
    DefineDocumentTypeInput,
)
from server.application.use_cases.get_extracted_data import GetExtractedData
from server.application.use_cases.process_uploaded_document import (
    ProcessUploadedDocument,
    ProcessUploadedDocumentInput,
)
from server.application.use_cases.register_client import (
    RegisterClient,
    RegisterClientInput,
)

__all__ = [
    "DefineDocumentType",
    "DefineDocumentTypeInput",
    "GetExtractedData",
    "ProcessUploadedDocument",
    "ProcessUploadedDocumentInput",
    "RegisterClient",
    "RegisterClientInput",
]
