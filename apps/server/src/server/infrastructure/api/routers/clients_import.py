from fastapi import APIRouter, Depends, HTTPException

from server.application.use_cases import ImportClientsFromDrive
from server.infrastructure.adapters.google_drive_client_directory import DriveDirectoryError
from server.infrastructure.api.auth_dependency import require_session
from server.infrastructure.api.deps import get_import_clients_use_case
from server.infrastructure.api.schemas import ClientImportResponse, ClientResponse

router = APIRouter(prefix="/clients", tags=["clients"], dependencies=[Depends(require_session)])


@router.post("/import", response_model=ClientImportResponse)
def import_clients_from_drive(
    use_case: ImportClientsFromDrive = Depends(get_import_clients_use_case),
) -> ClientImportResponse:
    """Mirrors the subfolders of the Drive clients folder into the client list."""
    try:
        result = use_case.execute()
    except DriveDirectoryError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None

    return ClientImportResponse(
        created=[ClientResponse.model_validate(c, from_attributes=True) for c in result.created],
        renamed=[ClientResponse.model_validate(c, from_attributes=True) for c in result.renamed],
        unchanged=result.unchanged,
    )
