from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from server.application.use_cases import DefineDocumentType, DefineDocumentTypeInput
from server.domain.ports import ConceptOption, DocumentContent
from server.infrastructure.api.auth_dependency import require_session
from server.infrastructure.api.deps import (
    get_define_document_type_use_case,
    get_document_type_repository,
    get_reconciliation_registry,
    get_save_concept_mapping_use_case,
)
from server.infrastructure.api.schemas import (
    DocumentTypeCreatedResponse,
    DocumentTypeResponse,
    ProposedFieldMappingResponse,
    UnmappedFieldResponse,
)
from server.reconciliation.application import SaveConceptMapping, SaveConceptMappingInput
from server.reconciliation.core.projection import ConceptMapping, ConceptMappingEntry
from server.reconciliation.core.registry import KindRegistry, UnknownReconciliationKind

router = APIRouter(
    prefix="/document-types", tags=["document-types"], dependencies=[Depends(require_session)]
)


@router.get("", response_model=list[DocumentTypeResponse])
def list_document_types(
    active_only: bool = True,
    document_types=Depends(get_document_type_repository),
) -> list[DocumentTypeResponse]:
    items = document_types.list_active() if active_only else document_types.list_all()
    return [DocumentTypeResponse.model_validate(t, from_attributes=True) for t in items]


@router.post("", response_model=DocumentTypeCreatedResponse, status_code=201)
def create_document_type(
    name: str = Form(...),
    description: str = Form(...),
    sample_file: UploadFile = File(...),
    kind_id: str | None = Form(None),
    use_case: DefineDocumentType = Depends(get_define_document_type_use_case),
    registry: KindRegistry = Depends(get_reconciliation_registry),
    save_mapping: SaveConceptMapping = Depends(get_save_concept_mapping_use_case),
) -> DocumentTypeCreatedResponse:
    # Sync on purpose: this calls a blocking AIProvider (httpx.Client) — a
    # `def` handler runs in FastAPI's threadpool instead of on the event
    # loop, unlike `async def`, which would stall every other request for
    # as long as the Claude call takes.
    sample_document = DocumentContent(
        data=sample_file.file.read(),
        mime_type=sample_file.content_type or "application/octet-stream",
        file_name=sample_file.filename or "sample",
    )
    kind = _resolve_kind(registry, kind_id)
    defined = use_case.execute(
        DefineDocumentTypeInput(
            name=name,
            description=description,
            sample_document=sample_document,
            concepts=_concept_options(kind),
        )
    )

    if kind is not None and defined.field_mappings:
        # Stored right away rather than left for a second call: a type saved
        # without its mapping extracts fields that reconcile against nothing,
        # and nothing in the UI would show that it is half-configured.
        save_mapping.execute(
            SaveConceptMappingInput(
                mapping=ConceptMapping(
                    document_type_id=defined.document_type.id,
                    kind_id=kind.id,
                    entries=tuple(
                        ConceptMappingEntry(
                            field_path=m.field_path,
                            concept_id=m.concept_id,
                            account_path=m.account_path,
                            sign=m.sign,
                        )
                        for m in defined.field_mappings
                    ),
                )
            )
        )

    return DocumentTypeCreatedResponse(
        **DocumentTypeResponse.model_validate(
            defined.document_type, from_attributes=True
        ).model_dump(),
        kind_id=kind.id if kind is not None else None,
        field_mappings=[
            ProposedFieldMappingResponse(
                field_path=m.field_path,
                concept_id=m.concept_id,
                account_path=m.account_path,
                sign=m.sign,
            )
            for m in defined.field_mappings
        ],
        unmapped_fields=[
            UnmappedFieldResponse(field_path=path, reason=reason)
            for path, reason in defined.unmapped_fields
        ],
    )


def _resolve_kind(registry: KindRegistry, kind_id: str | None):
    """The reconciliation model this type feeds, if any.

    Defaults to the only registered kind when there is exactly one, so the
    common case needs no extra field; once a second model exists the caller
    has to say which, rather than have one picked for it.
    """
    if kind_id is not None:
        try:
            return registry.get(kind_id)
        except UnknownReconciliationKind as exc:
            raise HTTPException(status_code=404, detail="Reconciliation kind not found") from exc
    kinds = registry.all()
    return kinds[0] if len(kinds) == 1 else None


def _concept_options(kind) -> tuple[ConceptOption, ...]:
    if kind is None:
        return ()
    return tuple(
        ConceptOption(id=c.id, label=c.label, description=c.description)
        for c in kind.concept_catalog().evidence_concepts
    )
