from fastapi import APIRouter, Depends, HTTPException

from server.application.use_cases import RegisterClient, RegisterClientInput
from server.infrastructure.api.auth_dependency import require_session
from server.infrastructure.api.deps import (
    get_client_repository,
    get_document_repository,
    get_register_client_use_case,
)
from server.infrastructure.api.schemas import ClientCreateRequest, ClientResponse, DocumentResponse

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
