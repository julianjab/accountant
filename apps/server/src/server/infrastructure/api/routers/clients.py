from fastapi import APIRouter, Depends, HTTPException

from server.application.use_cases import (
    ClientHasNoFolder,
    ClientNotFound,
    ImportClientDocuments,
    ImportClientDocumentsInput,
    ListClientSheetRows,
    ListClientSheetRowsInput,
    RegisterClient,
    RegisterClientInput,
)
from server.infrastructure.api.auth_dependency import require_session
from server.infrastructure.api.deps import (
    get_client_repository,
    get_document_repository,
    get_import_client_documents_use_case,
    get_list_client_sheet_rows_use_case,
    get_register_client_use_case,
)
from server.infrastructure.api.schemas import (
    ClientCreateRequest,
    ClientDocumentsImportResponse,
    ClientResponse,
    DocumentResponse,
    SheetRowResponse,
)

router = APIRouter(prefix="/clients", tags=["clients"], dependencies=[Depends(require_session)])


@router.post("", response_model=ClientResponse, status_code=201)
def create_client(
    payload: ClientCreateRequest,
    use_case: RegisterClient = Depends(get_register_client_use_case),
) -> ClientResponse:
    client = use_case.execute(
        RegisterClientInput(
            name=payload.name,
            tax_id=payload.tax_id,
            email=payload.email,
            drive_folder_url=payload.drive_folder_url,
            spreadsheet_url=payload.spreadsheet_url,
        )
    )
    return ClientResponse.model_validate(client, from_attributes=True)


@router.get("", response_model=list[ClientResponse])
def list_clients(
    clients=Depends(get_client_repository),
) -> list[ClientResponse]:
    return [ClientResponse.model_validate(c, from_attributes=True) for c in clients.list_all()]


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: str,
    clients=Depends(get_client_repository),
) -> ClientResponse:
    client = clients.get(client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return ClientResponse.model_validate(client, from_attributes=True)


@router.get("/{client_id}/documents", response_model=list[DocumentResponse])
def list_client_documents(
    client_id: str,
    clients=Depends(get_client_repository),
    documents=Depends(get_document_repository),
) -> list[DocumentResponse]:
    if clients.get(client_id) is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return [
        DocumentResponse.model_validate(d, from_attributes=True)
        for d in documents.list_by_client(client_id)
    ]


@router.get("/{client_id}/spreadsheet-rows", response_model=list[SheetRowResponse])
def list_client_spreadsheet_rows(
    client_id: str,
    use_case: ListClientSheetRows = Depends(get_list_client_sheet_rows_use_case),
) -> list[SheetRowResponse]:
    try:
        rows = use_case.execute(ListClientSheetRowsInput(client_id=client_id))
    except ClientNotFound as error:
        raise HTTPException(status_code=404, detail="Client not found") from error
    return [SheetRowResponse.model_validate(row, from_attributes=True) for row in rows]


@router.post("/{client_id}/documents/import", response_model=ClientDocumentsImportResponse)
def import_client_documents(
    client_id: str,
    reprocess: bool = False,
    use_case: ImportClientDocuments = Depends(get_import_client_documents_use_case),
) -> ClientDocumentsImportResponse:
    """Processes the files already in the client's folder.

    Change notifications only report what arrives after a subscription starts,
    so this is the only way documents that predate the watch ever enter the
    system.
    """
    try:
        result = use_case.execute(
            ImportClientDocumentsInput(client_id=client_id, reprocess=reprocess)
        )
    except ClientNotFound as exc:
        raise HTTPException(status_code=404, detail="Client not found") from exc
    except ClientHasNoFolder as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ClientDocumentsImportResponse(
        imported=[
            DocumentResponse.model_validate(d, from_attributes=True) for d in result.imported
        ],
        failed=[DocumentResponse.model_validate(d, from_attributes=True) for d in result.failed],
        skipped=result.skipped,
    )
