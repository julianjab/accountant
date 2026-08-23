from functools import lru_cache

from server.application.use_cases import (
    ApproveDocument,
    DefineDocumentType,
    GetExtractedData,
    ProcessUploadedDocument,
    RegisterClient,
)
from server.infrastructure.adapters.claude_document_classifier import (
    ClaudeDocumentClassifier,
)
from server.infrastructure.adapters.claude_document_type_configurator import (
    ClaudeDocumentTypeConfigurator,
)
from server.infrastructure.adapters.claude_ocr_engine import ClaudeOcrEngine
from server.infrastructure.adapters.google_drive_storage import GoogleDriveStorage
from server.infrastructure.adapters.in_memory_repositories import (
    InMemoryClientRepository,
    InMemoryDocumentRepository,
    InMemoryDocumentTypeRepository,
    InMemoryExtractedDataRepository,
)
from server.infrastructure.config.prompts import PromptsConfig, get_prompts
from server.infrastructure.config.settings import Settings
from server.infrastructure.providers.ai_provider import AIProvider
from server.infrastructure.providers.anthropic_provider import AnthropicProvider


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_prompts_config() -> PromptsConfig:
    return get_prompts()


@lru_cache
def get_ai_provider() -> AIProvider:
    return AnthropicProvider()


@lru_cache
def get_client_repository() -> InMemoryClientRepository:
    return InMemoryClientRepository()


@lru_cache
def get_document_repository() -> InMemoryDocumentRepository:
    return InMemoryDocumentRepository()


@lru_cache
def get_document_type_repository() -> InMemoryDocumentTypeRepository:
    return InMemoryDocumentTypeRepository()


@lru_cache
def get_extracted_data_repository() -> InMemoryExtractedDataRepository:
    return InMemoryExtractedDataRepository()


@lru_cache
def get_document_storage() -> GoogleDriveStorage:
    return GoogleDriveStorage(get_settings().google_service_account_file)


@lru_cache
def get_document_classifier() -> ClaudeDocumentClassifier:
    settings = get_settings()
    return ClaudeDocumentClassifier(
        get_ai_provider(), settings.anthropic_model, get_prompts_config().document_classification
    )


@lru_cache
def get_ocr_engine() -> ClaudeOcrEngine:
    settings = get_settings()
    return ClaudeOcrEngine(
        get_ai_provider(), settings.anthropic_model, get_prompts_config().ocr_extraction
    )


@lru_cache
def get_document_type_configurator() -> ClaudeDocumentTypeConfigurator:
    settings = get_settings()
    return ClaudeDocumentTypeConfigurator(
        get_ai_provider(),
        settings.anthropic_model,
        get_prompts_config().document_type_configuration,
    )


def get_register_client_use_case() -> RegisterClient:
    return RegisterClient(get_client_repository())


def get_define_document_type_use_case() -> DefineDocumentType:
    return DefineDocumentType(get_document_type_configurator(), get_document_type_repository())


def get_process_uploaded_document_use_case() -> ProcessUploadedDocument:
    return ProcessUploadedDocument(
        storage=get_document_storage(),
        classifier=get_document_classifier(),
        ocr=get_ocr_engine(),
        documents=get_document_repository(),
        document_types=get_document_type_repository(),
        extracted_data=get_extracted_data_repository(),
    )


def get_extracted_data_use_case() -> GetExtractedData:
    return GetExtractedData(get_extracted_data_repository())


def get_approve_document_use_case() -> ApproveDocument:
    return ApproveDocument(get_document_repository())
