import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from server.application.use_cases import (
    DefineDocumentType,
    DefineDocumentTypeInput,
    DocumentTypeNotFound,
    ProposeDocumentType,
    ProposeDocumentTypeInput,
    UpdateDocumentType,
    UpdateDocumentTypeInput,
)
from server.domain.ports import ConceptOption, DocumentContent, ProposedFieldMapping
from server.infrastructure.api.auth_dependency import require_session
from server.infrastructure.api.deps import (
    get_define_document_type_use_case,
    get_document_type_repository,
    get_propose_document_type_use_case,
    get_prune_concept_mappings_use_case,
    get_reconciliation_registry,
    get_save_concept_mapping_use_case,
    get_update_document_type_use_case,
)
from server.infrastructure.api.schemas import (
    DocumentTypeCreatedResponse,
    DocumentTypeCreateRequest,
    DocumentTypeProposalResponse,
    DocumentTypeResponse,
    DocumentTypeUpdatedResponse,
    DocumentTypeUpdateRequest,
    MappingChangeResponse,
    ProposedFieldMappingResponse,
    ProposedFieldResponse,
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


@router.post("/proposals", response_model=DocumentTypeProposalResponse)
def propose_document_type(
    name: str = Form(...),
    sample_file: UploadFile = File(...),
    kind_id: str | None = Form(None),
    use_case: ProposeDocumentType = Depends(get_propose_document_type_use_case),
    registry: KindRegistry = Depends(get_reconciliation_registry),
) -> DocumentTypeProposalResponse:
    """Reads a sample and reports what could be configured, storing nothing.

    A proposal routinely lists twenty fields where the accountant wants the
    identifier and three figures. Saving it whole made pruning the type their
    problem afterwards; this makes choosing it their decision up front.

    Sync on purpose, like the create handler: this calls a blocking AIProvider,
    and a `def` handler runs in FastAPI's threadpool rather than stalling the
    event loop for the length of the Claude call.
    """
    kind = _resolve_kind(registry, kind_id)
    proposal = use_case.execute(
        ProposeDocumentTypeInput(
            type_name=name,
            sample_document=DocumentContent(
                data=sample_file.file.read(),
                mime_type=sample_file.content_type or "application/octet-stream",
                file_name=sample_file.filename or "sample",
            ),
            concepts=_concept_options(kind),
        )
    )
    return DocumentTypeProposalResponse(
        extraction_prompt=proposal.extraction_prompt,
        extraction_schema=proposal.extraction_schema,
        fields=[
            ProposedFieldResponse(
                path=f.path,
                label=f.label,
                role=f.role.value,
                sample_value=f.sample_value,
                section=f.section,
            )
            for f in proposal.fields
        ],
        field_mappings=[
            ProposedFieldMappingResponse(
                field_path=m.field_path,
                concept_id=m.concept_id,
                account_path=m.account_path,
                sign=m.sign,
            )
            for m in proposal.field_mappings
        ],
        unmapped_fields=[
            UnmappedFieldResponse(field_path=path, reason=reason)
            for path, reason in proposal.unmapped_fields
        ],
        kind_id=kind.id if kind is not None else None,
        reporter_path=proposal.reporter_path,
        reporter_name_path=proposal.reporter_name_path,
        period_path=proposal.period_path,
    )


@router.post("", response_model=DocumentTypeCreatedResponse, status_code=201)
def create_document_type(
    payload: DocumentTypeCreateRequest,
    use_case: DefineDocumentType = Depends(get_define_document_type_use_case),
    registry: KindRegistry = Depends(get_reconciliation_registry),
    save_mapping: SaveConceptMapping = Depends(get_save_concept_mapping_use_case),
) -> DocumentTypeCreatedResponse:
    """Saves the configuration someone reviewed on /document-types/proposals.

    No AI call: what was approved is what is stored. Re-proposing here would
    save a different configuration from the one on screen, and would charge
    for a second run of the model to do it.
    """
    name = payload.name
    description = payload.description
    kind_id = payload.kind_id
    tax_years = tuple(sorted(set(payload.tax_years)))
    sample_document_id = payload.sample_document_id
    kind = _resolve_kind(registry, kind_id)
    defined = use_case.execute(
        DefineDocumentTypeInput(
            name=name,
            description=description,
            extraction_prompt=payload.extraction_prompt,
            extraction_schema=payload.extraction_schema,
            field_mappings=tuple(
                ProposedFieldMapping(
                    field_path=m.field_path,
                    concept_id=m.concept_id,
                    account_path=m.account_path,
                    sign=m.sign,
                )
                for m in payload.field_mappings
            ),
            reporter_path=payload.reporter_path,
            reporter_name_path=payload.reporter_name_path,
            period_path=payload.period_path,
            concepts=_concept_options(kind),
            tax_years=tax_years,
            sample_document_id=sample_document_id,
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
                # Tuple because the entity and the Firestore adapter both
                # assume one, and None must keep meaning "untouched" so that
                # an empty list can mean "applies to any year".
                tax_years=(tuple(payload.tax_years) if payload.tax_years is not None else None),
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


def _parse_years(raw: str) -> tuple[int, ...]:
    """Reads `2024,2025` from a form field. Empty means any year."""
    years = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            years.append(int(part))
    return tuple(sorted(set(years)))


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
