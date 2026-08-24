from datetime import timedelta
from functools import lru_cache

from google.cloud.firestore import Client as FirestoreClient

from server.application.use_cases import (
    ApproveDocument,
    CompleteGoogleSignIn,
    DefineDocumentType,
    DeleteDocumentType,
    GetDocumentMetrics,
    GetExtractedData,
    GetGoogleSession,
    ImportClientDocuments,
    ImportClientsFromDrive,
    ListClientSheetRows,
    ProcessDriveChangeNotification,
    ProcessUploadedDocument,
    ProposeDocumentType,
    ReadStoredDocument,
    RecognizeDocumentSource,
    RegisterClient,
    SignOutGoogle,
    StartGoogleSignIn,
    SubscribeDriveWebhook,
    UpdateDocumentType,
)
from server.domain.ports import (
    ClientRepository,
    DocumentRepository,
    DocumentTypeRepository,
    DriveFileClaimRepository,
    DriveWatchChannelRepository,
    DriveWatcher,
    ExtractedDataRepository,
    GoogleOAuthClient,
    SessionRepository,
)
from server.infrastructure.adapters.claude_document_classifier import (
    ClaudeDocumentClassifier,
)
from server.infrastructure.adapters.claude_document_type_configurator import (
    ClaudeDocumentTypeConfigurator,
)
from server.infrastructure.adapters.claude_ocr_engine import ClaudeOcrEngine
from server.infrastructure.adapters.firestore_repositories import (
    FirestoreClientRepository,
    FirestoreDocumentRepository,
    FirestoreDocumentTypeRepository,
    FirestoreDriveFileClaimRepository,
    FirestoreDriveWatchChannelRepository,
    FirestoreExtractedDataRepository,
    FirestoreSessionRepository,
)
from server.infrastructure.adapters.google_drive_client_directory import (
    GoogleDriveClientDirectory,
)
from server.infrastructure.adapters.google_drive_storage import (
    GoogleDriveStorage,
    GoogleDriveWatcher,
)
from server.infrastructure.adapters.google_oauth_client import HttpGoogleOAuthClient
from server.infrastructure.adapters.in_memory_repositories import (
    InMemoryClientRepository,
    InMemoryDocumentRepository,
    InMemoryDocumentTypeRepository,
    InMemoryDriveFileClaimRepository,
    InMemoryDriveWatchChannelRepository,
    InMemoryExtractedDataRepository,
    InMemorySessionRepository,
)
from server.infrastructure.config.prompts import PromptsConfig, get_prompts
from server.infrastructure.config.settings import Settings
from server.infrastructure.providers.ai_provider import AIProvider
from server.infrastructure.providers.anthropic_provider import AnthropicProvider
from server.reconciliation.application import (
    ConceptMappingRepository,
    GetConceptMapping,
    GetReconciliationReport,
    PruneConceptMappings,
    ReconcileClientPeriod,
    ReconciliationReportRepository,
    SaveConceptMapping,
)
from server.reconciliation.core.registry import KindRegistry
from server.reconciliation.infrastructure import (
    DeleteDocumentTypeAndMappings,
    DocumentFactProvider,
    InMemoryConceptMappingRepository,
    InMemoryReconciliationReportRepository,
    KindSourceParsers,
    RecognizeDocumentSourceAndReconcile,
)
from server.reconciliation.infrastructure.firestore_repositories import (
    FirestoreConceptMappingRepository,
    FirestoreReconciliationReportRepository,
)
from server.reconciliation.kinds.exogena import ExogenaReconciliation


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_prompts_config() -> PromptsConfig:
    return get_prompts()


@lru_cache
def get_firestore() -> FirestoreClient | None:
    """The Firestore client, or None when no project is configured.

    Returning None here is what keeps the in-memory fallback a one-line decision
    at each repository provider instead of a parallel wiring path.
    """
    settings = get_settings()
    if not settings.firestore_project:
        return None
    return FirestoreClient(project=settings.firestore_project, database=settings.firestore_database)


@lru_cache
def get_ai_provider() -> AIProvider:
    return AnthropicProvider()


@lru_cache
def get_client_repository() -> ClientRepository:
    db = get_firestore()
    return InMemoryClientRepository() if db is None else FirestoreClientRepository(db)


@lru_cache
def get_document_repository() -> DocumentRepository:
    db = get_firestore()
    return InMemoryDocumentRepository() if db is None else FirestoreDocumentRepository(db)


@lru_cache
def get_document_type_repository() -> DocumentTypeRepository:
    db = get_firestore()
    return InMemoryDocumentTypeRepository() if db is None else FirestoreDocumentTypeRepository(db)


@lru_cache
def get_extracted_data_repository() -> ExtractedDataRepository:
    db = get_firestore()
    return InMemoryExtractedDataRepository() if db is None else FirestoreExtractedDataRepository(db)


@lru_cache
def get_drive_watch_channel_repository() -> DriveWatchChannelRepository:
    db = get_firestore()
    return (
        InMemoryDriveWatchChannelRepository()
        if db is None
        else FirestoreDriveWatchChannelRepository(db)
    )


@lru_cache
def get_drive_file_claim_repository() -> DriveFileClaimRepository:
    db = get_firestore()
    return (
        InMemoryDriveFileClaimRepository() if db is None else FirestoreDriveFileClaimRepository(db)
    )


@lru_cache
def get_document_storage() -> GoogleDriveStorage:
    return GoogleDriveStorage(get_settings().google_service_account_file)


@lru_cache
def get_drive_watcher() -> DriveWatcher:
    return GoogleDriveWatcher(get_settings().google_service_account_file)


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


def get_update_document_type_use_case() -> UpdateDocumentType:
    return UpdateDocumentType(get_document_type_repository())


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


def get_document_metrics_use_case() -> GetDocumentMetrics:
    return GetDocumentMetrics(get_document_repository())


@lru_cache
def get_session_repository() -> SessionRepository:
    db = get_firestore()
    return InMemorySessionRepository() if db is None else FirestoreSessionRepository(db)


@lru_cache
def get_google_oauth_client() -> GoogleOAuthClient:
    settings = get_settings()
    return HttpGoogleOAuthClient(
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        redirect_uri=settings.google_oauth_redirect_uri,
    )


def get_start_google_sign_in_use_case() -> StartGoogleSignIn:
    return StartGoogleSignIn(get_google_oauth_client())


def get_complete_google_sign_in_use_case() -> CompleteGoogleSignIn:
    return CompleteGoogleSignIn(
        get_google_oauth_client(), get_session_repository(), get_settings().allows
    )


def get_google_session_use_case() -> GetGoogleSession:
    return GetGoogleSession(
        get_google_oauth_client(),
        get_session_repository(),
        timedelta(days=get_settings().session_max_age_days),
    )


def get_sign_out_google_use_case() -> SignOutGoogle:
    return SignOutGoogle(get_google_oauth_client(), get_session_repository())


def get_subscribe_drive_webhook_use_case() -> SubscribeDriveWebhook:
    return SubscribeDriveWebhook(get_drive_watcher(), get_drive_watch_channel_repository())


@lru_cache
def get_process_drive_change_notification_use_case() -> ProcessDriveChangeNotification:
    # Must be a singleton: its per-channel locks (guarding against two
    # concurrent Drive notifications racing on the same cursor) only work if
    # every request shares the same instance instead of getting a fresh one
    # with an empty lock table.
    return ProcessDriveChangeNotification(
        channels=get_drive_watch_channel_repository(),
        change_reader=get_drive_watcher(),
        claims=get_drive_file_claim_repository(),
        documents=get_document_repository(),
        process_document=get_process_uploaded_document_use_case(),
    )


@lru_cache
def get_client_directory() -> GoogleDriveClientDirectory:
    settings = get_settings()
    return GoogleDriveClientDirectory(
        settings.google_service_account_file, settings.google_drive_clients_folder_id
    )


def get_propose_document_type_use_case() -> ProposeDocumentType:
    return ProposeDocumentType(get_document_type_configurator())


def get_import_client_documents_use_case() -> ImportClientDocuments:
    return ImportClientDocuments(
        clients=get_client_repository(),
        documents=get_document_repository(),
        storage=get_document_storage(),
        process_document=get_process_uploaded_document_use_case(),
    )


def get_import_clients_use_case() -> ImportClientsFromDrive:
    return ImportClientsFromDrive(get_client_directory(), get_client_repository())


def get_list_client_sheet_rows_use_case() -> ListClientSheetRows:
    return ListClientSheetRows(
        get_client_repository(), get_document_repository(), get_extracted_data_repository()
    )


@lru_cache
def get_reconciliation_registry() -> KindRegistry:
    """The one place concrete reconciliation kinds are named.

    Composition happens here so that neither the engine nor the API knows which
    models exist; adding one is a line in this list.
    """
    return KindRegistry([ExogenaReconciliation()])


@lru_cache
def get_concept_mapping_repository() -> ConceptMappingRepository:
    db = get_firestore()
    return (
        InMemoryConceptMappingRepository() if db is None else FirestoreConceptMappingRepository(db)
    )


@lru_cache
def get_reconciliation_report_repository() -> ReconciliationReportRepository:
    db = get_firestore()
    return (
        InMemoryReconciliationReportRepository()
        if db is None
        else FirestoreReconciliationReportRepository(db)
    )


def get_reconciliation_fact_provider() -> DocumentFactProvider:
    return DocumentFactProvider(
        registry=get_reconciliation_registry(),
        clients=get_client_repository(),
        documents=get_document_repository(),
        document_types=get_document_type_repository(),
        extracted_data=get_extracted_data_repository(),
        mappings=get_concept_mapping_repository(),
        storage=get_document_storage(),
    )


def get_reconcile_client_period_use_case() -> ReconcileClientPeriod:
    return ReconcileClientPeriod(
        registry=get_reconciliation_registry(),
        facts=get_reconciliation_fact_provider(),
        reports=get_reconciliation_report_repository(),
        mappings=get_concept_mapping_repository(),
    )


def get_concept_mapping_use_case() -> GetConceptMapping:
    return GetConceptMapping(get_reconciliation_registry(), get_concept_mapping_repository())


def get_reconciliation_report_use_case() -> GetReconciliationReport:
    return GetReconciliationReport(
        get_reconciliation_registry(), get_reconciliation_report_repository()
    )


def get_save_concept_mapping_use_case() -> SaveConceptMapping:
    return SaveConceptMapping(get_reconciliation_registry(), get_concept_mapping_repository())


def get_prune_concept_mappings_use_case() -> PruneConceptMappings:
    return PruneConceptMappings(get_reconciliation_registry(), get_concept_mapping_repository())


@lru_cache
def get_source_parsers() -> KindSourceParsers:
    """The formats the server reads without an AI, offered to intake.

    Composed from the reconciliation kinds because that is where such a parser
    lives — a kind owns the report it reconciles against. Intake only needs to
    know that some file formats can be read exactly.
    """
    return KindSourceParsers(get_reconciliation_registry())


def get_recognize_document_source_use_case() -> RecognizeDocumentSourceAndReconcile:
    """Recognising a document also rebuilds the reports it just changed.

    Wired here rather than left to the caller: naming the exogena is the one
    act that makes a client's whole reconciliation computable, and every screen
    that would show what the client still owes reads a report that would
    otherwise not exist yet.
    """
    return RecognizeDocumentSourceAndReconcile(
        recognize=RecognizeDocumentSource(
            documents=get_document_repository(),
            storage=get_document_storage(),
            parsers=get_source_parsers(),
            extracted_data=get_extracted_data_repository(),
        ),
        reconcile=get_reconcile_client_period_use_case(),
        registry=get_reconciliation_registry(),
    )


def get_read_stored_document_use_case() -> ReadStoredDocument:
    return ReadStoredDocument(get_document_repository(), get_document_storage())


def get_delete_document_type_use_case() -> DeleteDocumentTypeAndMappings:
    return DeleteDocumentTypeAndMappings(
        DeleteDocumentType(get_document_type_repository(), get_document_repository()),
        get_concept_mapping_repository(),
    )
