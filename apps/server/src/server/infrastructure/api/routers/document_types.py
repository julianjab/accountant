import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from server.application.use_cases import (
    DefineDocumentType,
    DefineDocumentTypeInput,
    DocumentTypeNotFound,
    UpdateDocumentType,
    UpdateDocumentTypeInput,
)
from server.domain.ports import ConceptOption, DocumentContent
from server.infrastructure.api.auth_dependency import require_session
from server.infrastructure.api.deps import (
    get_define_document_type_use_case,
    get_document_type_repository,
    get_prune_concept_mappings_use_case,
    get_reconciliation_registry,
    get_save_concept_mapping_use_case,
    get_update_document_type_use_case,
)
from server.infrastructure.api.schemas import (
    DocumentTypeCreatedResponse,
    DocumentTypeResponse,
    DocumentTypeUpdatedResponse,
    DocumentTypeUpdateRequest,
    MappingChangeResponse,
    ProposedFieldMappingResponse,
    UnmappedFieldResponse,
)
from server.reconciliation.application import (
    MappingChange,
    MappingChangeKind,
    PruneConceptMappings,
    PruneConceptMappingsInput,
    SaveConceptMapping,
    SaveConceptMappingInput,
)
from server.reconciliation.core.projection import ConceptMapping, ConceptMappingEntry
from server.reconciliation.core.registry import KindRegistry, UnknownReconciliationKind

logger = logging.getLogger(__name__)

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

    stored_mappings = defined.field_mappings
    unmapped = list(defined.unmapped_fields)

    if defined.field_mappings and defined.reporter_path is None:
        # Every fact needs a party to attribute it to, so a mapping without
        # one is discarded whole by the projection. Storing it anyway would
        # leave the type looking configured, its mappings visible in the UI,
        # and every claim reported as missing evidence with nothing pointing
        # at the cause — which is what happened the first time this ran.
        logger.warning(
            "The proposal named no reporting party, so its mappings cannot be used",
            extra={"document_type_id": defined.document_type.id},
        )
        unmapped.extend(
            (m.field_path, "the document does not say who reports these amounts")
            for m in defined.field_mappings
        )
        stored_mappings = ()
    elif kind is not None and defined.field_mappings:
        # Stored right away rather than left for a second call: a type saved
        # without its mapping extracts fields that reconcile against nothing,
        # and nothing in the UI would show that it is half-configured.
        try:
            save_mapping.execute(
                SaveConceptMappingInput(
                    mapping=ConceptMapping(
                        document_type_id=defined.document_type.id,
                        kind_id=kind.id,
                        reporter_path=defined.reporter_path,
                        reporter_name_path=defined.reporter_name_path,
                        period_path=defined.period_path,
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
        except Exception:
            # The document type is already saved and there is no transaction
            # across the two contexts, so failing the request now would report
            # an error while leaving the type created — and hide that its
            # mapping is missing. Reporting the mappings as unstored says
            # exactly what happened, and the mapping endpoint can set them
            # later without redoing the AI call.
            logger.exception(
                "Saved the document type but could not store its concept mapping",
                extra={"document_type_id": defined.document_type.id, "kind_id": kind.id},
            )
            unmapped.extend(
                (m.field_path, "the mapping could not be stored; set it again to retry")
                for m in defined.field_mappings
            )
            stored_mappings = ()

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
            for m in stored_mappings
        ],
        unmapped_fields=[
            UnmappedFieldResponse(field_path=path, reason=reason) for path, reason in unmapped
        ],
    )


@router.patch("/{document_type_id}", response_model=DocumentTypeUpdatedResponse)
def update_document_type(
    document_type_id: str,
    payload: DocumentTypeUpdateRequest,
    use_case: UpdateDocumentType = Depends(get_update_document_type_use_case),
    prune: PruneConceptMappings = Depends(get_prune_concept_mappings_use_case),
) -> DocumentTypeUpdatedResponse:
    try:
        updated = use_case.execute(
            UpdateDocumentTypeInput(
                document_type_id=document_type_id,
                name=payload.name,
                description=payload.description,
                active=payload.active,
                extraction_prompt=payload.extraction_prompt,
                extraction_schema=payload.extraction_schema,
            )
        )
    except DocumentTypeNotFound as exc:
        raise HTTPException(status_code=404, detail="Document type not found") from exc

    changes: tuple[MappingChange, ...] = ()
    if payload.extraction_schema is not None:
        changes = _prune_mappings(prune, document_type_id, updated.extraction_schema)

    return DocumentTypeUpdatedResponse(
        **DocumentTypeResponse.model_validate(updated, from_attributes=True).model_dump(),
        mapping_changes=[
            MappingChangeResponse(
                kind_id=c.kind_id,
                change=str(c.change),
                path=c.path,
                field_path=c.field_path,
                concept_id=c.concept_id,
                reason=c.reason,
            )
            for c in changes
        ],
    )


def _prune_mappings(
    prune: PruneConceptMappings, document_type_id: str, schema: dict
) -> tuple[MappingChange, ...]:
    """Realign the stored concept mappings with the schema just saved.

    Reported rather than raised, for the same reason creation reports a mapping
    it could not store: the type is already saved, there is no transaction
    across the two contexts, and a 500 here would leave the caller believing
    the edit failed while its mappings still point at fields that are gone.
    """
    try:
        return prune.execute(
            PruneConceptMappingsInput(document_type_id=document_type_id, extraction_schema=schema)
        )
    except Exception:
        logger.exception(
            "Saved the document type but could not realign its concept mappings",
            extra={"document_type_id": document_type_id},
        )
        return (
            MappingChange(
                kind_id="",
                change=MappingChangeKind.PRUNE_FAILED,
                reason=(
                    "the concept mappings could not be checked against the new schema; they may "
                    "still point at fields it no longer declares"
                ),
            ),
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
