from fastapi import APIRouter, Depends

from server.application.use_cases import RegisterClient, RegisterClientInput
from server.infrastructure.api.deps import (
    get_client_repository,
    get_register_client_use_case,
)
from server.infrastructure.api.schemas import ClientCreateRequest, ClientResponse

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("", response_model=ClientResponse, status_code=201)
def create_client(
    payload: ClientCreateRequest,
    use_case: RegisterClient = Depends(get_register_client_use_case),
) -> ClientResponse:
    client = use_case.execute(
        RegisterClientInput(name=payload.name, tax_id=payload.tax_id, email=payload.email)
    )
    return ClientResponse.model_validate(client, from_attributes=True)


@router.get("", response_model=list[ClientResponse])
def list_clients(
    clients=Depends(get_client_repository),
) -> list[ClientResponse]:
    return [ClientResponse.model_validate(c, from_attributes=True) for c in clients.list_all()]
