import logging
from dataclasses import dataclass

from server.application.use_cases.list_client_sheet_rows import ClientNotFound
from server.application.use_cases.process_uploaded_document import (
    ProcessUploadedDocument,
    ProcessUploadedDocumentInput,
)
from server.domain.entities import Document, DocumentStatus
from server.domain.ports import ClientRepository, DocumentRepository, DocumentStorage

logger = logging.getLogger(__name__)


class ClientHasNoFolder(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ImportClientDocumentsInput:
    client_id: str
    #: Reprocess files that already produced a document. Off by default so a
    #: repeated import is cheap and does not re-run OCR over everything.
    reprocess: bool = False


@dataclass(frozen=True, slots=True)
class ImportClientDocumentsResult:
    imported: list[Document]
    skipped: int
    failed: list[Document]


class ImportClientDocuments:
    """Processes the files already sitting in a client's storage folder.

    Drive change notifications only ever report what happens *after* a
    subscription starts, so everything already in a folder when a client is
    imported is invisible to that feed forever. Without this, the only
    documents the system can ever see are ones uploaded while a watch happened
    to be active — which is why a client can show a linked folder full of
    files and no documents at all.

    Safe to run repeatedly: a file that already produced a document is skipped
    unless the caller explicitly asks for a reprocess.
    """

    def __init__(
        self,
        clients: ClientRepository,
        documents: DocumentRepository,
        storage: DocumentStorage,
        process_document: ProcessUploadedDocument,
    ) -> None:
        self._clients = clients
        self._documents = documents
        self._storage = storage
        self._process_document = process_document

    def execute(self, data: ImportClientDocumentsInput) -> ImportClientDocumentsResult:
        client = self._clients.get(data.client_id)
        if client is None:
            raise ClientNotFound(data.client_id)
        if not client.drive_folder_id:
            raise ClientHasNoFolder(f"Client {data.client_id} is not linked to a storage folder")

        imported: list[Document] = []
        failed: list[Document] = []
        skipped = 0

        for file in self._storage.list_files(client.drive_folder_id):
            if self._should_skip(file.id, client.id, reprocess=data.reprocess):
                skipped += 1
                continue
            document = self._process_one(client.id, file.id, replace=data.reprocess)
            if document is None:
                continue
            (failed if document.status == DocumentStatus.FAILED else imported).append(document)

        logger.info(
            "Imported client documents",
            extra={
                "client_id": client.id,
                "imported": len(imported),
                "failed": len(failed),
                "skipped": skipped,
            },
        )
        return ImportClientDocumentsResult(imported=imported, skipped=skipped, failed=failed)

    def _should_skip(self, drive_file_id: str, client_id: str, *, reprocess: bool) -> bool:
        existing = self._documents.get_by_drive_file_id_and_client(drive_file_id, client_id)
        if existing is None:
            return False
        # An approved document carries a person's review. Re-running OCR over
        # it would reset it to CLASSIFYING and drop the approval with no record
        # that it ever happened, so approval is never overridden — not even by
        # an explicit reprocess. Undoing it has to be a deliberate act of its
        # own, not a side effect of re-importing a folder.
        if existing.status == DocumentStatus.APPROVED:
            return True
        if existing.status == DocumentStatus.PROCESSED:
            return not reprocess
        # Anything else is unfinished or failed, and worth another attempt.
        return False

    def _process_one(self, client_id: str, drive_file_id: str, *, replace: bool) -> Document | None:
        try:
            return self._process_document.execute(
                ProcessUploadedDocumentInput(
                    client_id=client_id,
                    drive_file_id=drive_file_id,
                    file_reference=drive_file_id,
                    # Without this a reprocess would leave a second document
                    # behind for the same file on every run.
                    replace_existing=replace,
                )
            )
        except Exception:
            # Only the download can still raise: ProcessUploadedDocument turns
            # everything past that point into a FAILED document. One
            # unreachable file must not abandon the rest of the folder, so this
            # is logged and the import continues.
            logger.exception(
                "Could not read file during import",
                extra={"client_id": client_id, "drive_file_id": drive_file_id},
            )
            return None
