"""HTTP surface for reconciliation.

Sits with the other routers rather than under `server.reconciliation` because
intake has not been moved to a module-first layout yet, and splitting the
FastAPI wiring across two conventions would be worse than the asymmetry. The
import-linter contracts still hold: this is infrastructure, and nothing in
`server.domain` or `server.application` reaches the other way.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException

from server.infrastructure.api.auth_dependency import require_session
from server.infrastructure.api.deps import (
    get_concept_mapping_use_case,
    get_reconcile_client_period_use_case,
    get_reconciliation_registry,
    get_reconciliation_report_use_case,
    get_save_concept_mapping_use_case,
)
from server.infrastructure.api.schemas import (
    ConceptMappingEntryPayload,
    ConceptMappingRequest,
    ConceptMappingResponse,
    ReconciliationConceptResponse,
    ReconciliationFactResponse,
    ReconciliationFindingResponse,
    ReconciliationKindResponse,
    ReconciliationReportResponse,
    ReconciliationSummaryResponse,
)
from server.reconciliation.application import (
    GetConceptMapping,
    GetConceptMappingInput,
    GetReconciliationReport,
    GetReconciliationReportInput,
    ReconcileClientPeriod,
    ReconcileClientPeriodInput,
    SaveConceptMapping,
    SaveConceptMappingInput,
    UnknownMappedConcept,
)
from server.reconciliation.core.findings import ReconciliationFinding, ReconciliationReport
from server.reconciliation.core.projection import ConceptMapping, ConceptMappingEntry
from server.reconciliation.core.registry import KindRegistry, UnknownReconciliationKind
from server.shared import FinancialFact, Period

router = APIRouter(
    prefix="/reconciliation", tags=["reconciliation"], dependencies=[Depends(require_session)]
)

_PERIOD = re.compile(r"^(\d{4})(?:-(\d{2}))?$")


def _parse_period(raw: str) -> Period:
    match = _PERIOD.match(raw)
    if match is None:
        raise HTTPException(status_code=422, detail="Period must be `YYYY` or `YYYY-MM`")
    year, month = int(match.group(1)), match.group(2)
    try:
        return Period.of_year(year) if month is None else Period.of_month(year, int(month))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _resolve_kind(registry: KindRegistry, kind_id: str):
    try:
        return registry.get(kind_id)
    except UnknownReconciliationKind as exc:
        raise HTTPException(status_code=404, detail="Reconciliation kind not found") from exc


@router.get("/kinds", response_model=list[ReconciliationKindResponse])
def list_kinds(
    registry: KindRegistry = Depends(get_reconciliation_registry),
) -> list[ReconciliationKindResponse]:
    return [_to_kind_response(kind) for kind in registry.all()]


@router.get("/kinds/{kind_id}", response_model=ReconciliationKindResponse)
def get_kind(
    kind_id: str,
    registry: KindRegistry = Depends(get_reconciliation_registry),
) -> ReconciliationKindResponse:
    return _to_kind_response(_resolve_kind(registry, kind_id))


@router.get(
    "/kinds/{kind_id}/clients/{client_id}/periods/{period}",
    response_model=ReconciliationReportResponse,
)
def get_report(
    kind_id: str,
    client_id: str,
    period: str,
    registry: KindRegistry = Depends(get_reconciliation_registry),
    use_case: GetReconciliationReport = Depends(get_reconciliation_report_use_case),
) -> ReconciliationReportResponse:
    _resolve_kind(registry, kind_id)
    report = use_case.execute(
        GetReconciliationReportInput(
            client_id=client_id, kind_id=kind_id, period=_parse_period(period)
        )
    )
    if report is None:
        raise HTTPException(
            status_code=404, detail="No reconciliation has been run for this client and period"
        )
    return _to_report_response(report)


@router.post(
    "/kinds/{kind_id}/clients/{client_id}/periods/{period}",
    response_model=ReconciliationReportResponse,
)
def run_reconciliation(
    kind_id: str,
    client_id: str,
    period: str,
    registry: KindRegistry = Depends(get_reconciliation_registry),
    use_case: ReconcileClientPeriod = Depends(get_reconcile_client_period_use_case),
) -> ReconciliationReportResponse:
    _resolve_kind(registry, kind_id)
    try:
        report = use_case.execute(
            ReconcileClientPeriodInput(
                client_id=client_id, kind_id=kind_id, period=_parse_period(period)
            )
        )
    except ValueError as exc:
        # The kind reconciles by a different granularity than the one asked for.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_report_response(report)


@router.get(
    "/kinds/{kind_id}/document-types/{document_type_id}/mapping",
    response_model=ConceptMappingResponse,
)
def get_concept_mapping(
    kind_id: str,
    document_type_id: str,
    use_case: GetConceptMapping = Depends(get_concept_mapping_use_case),
) -> ConceptMappingResponse:
    try:
        mapping = use_case.execute(
            GetConceptMappingInput(document_type_id=document_type_id, kind_id=kind_id)
        )
    except UnknownReconciliationKind as exc:
        raise HTTPException(status_code=404, detail="Reconciliation kind not found") from exc
    if mapping is None:
        raise HTTPException(status_code=404, detail="Concept mapping not found")
    return _to_mapping_response(mapping)


@router.put(
    "/kinds/{kind_id}/document-types/{document_type_id}/mapping",
    response_model=ConceptMappingResponse,
)
def save_concept_mapping(
    kind_id: str,
    document_type_id: str,
    payload: ConceptMappingRequest,
    use_case: SaveConceptMapping = Depends(get_save_concept_mapping_use_case),
) -> ConceptMappingResponse:
    mapping = ConceptMapping(
        document_type_id=document_type_id,
        kind_id=kind_id,
        reporter_path=payload.reporter_path,
        reporter_name_path=payload.reporter_name_path,
        period_path=payload.period_path,
        entries=tuple(_entry_from_payload(e) for e in payload.entries),
    )
    try:
        saved = use_case.execute(SaveConceptMappingInput(mapping=mapping))
    except UnknownReconciliationKind as exc:
        raise HTTPException(status_code=404, detail="Reconciliation kind not found") from exc
    except UnknownMappedConcept as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_mapping_response(saved)


def _entry_from_payload(payload: ConceptMappingEntryPayload) -> ConceptMappingEntry:
    return ConceptMappingEntry(
        field_path=payload.field_path,
        concept_id=payload.concept_id,
        account_path=payload.account_path,
        sign=payload.sign,
    )


def _to_kind_response(kind) -> ReconciliationKindResponse:
    catalog = kind.concept_catalog()
    return ReconciliationKindResponse(
        id=kind.id,
        label=kind.label,
        period_granularity=kind.period_granularity.value,
        spine_concepts=[_to_concept_response(c) for c in catalog.spine_concepts],
        evidence_concepts=[_to_concept_response(c) for c in catalog.evidence_concepts],
    )


def _to_concept_response(concept) -> ReconciliationConceptResponse:
    return ReconciliationConceptResponse(
        id=concept.id,
        label=concept.label,
        role=concept.role.value,
        description=concept.description,
    )


def _to_report_response(report: ReconciliationReport) -> ReconciliationReportResponse:
    summary = report.summary
    return ReconciliationReportResponse(
        id=report.id,
        client_id=report.client_id,
        kind_id=report.kind_id,
        period=report.period.key,
        generated_at=report.generated_at,
        summary=ReconciliationSummaryResponse(
            counts={status.value: count for status, count in summary.counts.items()},
            total_findings=summary.total_findings,
            reconciled=summary.reconciled,
            needing_attention=summary.needing_attention,
        ),
        findings=[_to_finding_response(f) for f in report.findings],
    )


def _to_finding_response(finding: ReconciliationFinding) -> ReconciliationFindingResponse:
    return ReconciliationFindingResponse(
        id=finding.id,
        status=finding.status.value,
        rule_id=finding.rule_id,
        label=finding.label,
        reporter_tax_id=finding.reporter_tax_id.value,
        reporter_name=finding.reporter_name,
        spine_amount=str(finding.spine_amount.amount),
        evidence_amount=str(finding.evidence_amount.amount),
        delta=str(finding.delta.amount),
        account=finding.account.raw if finding.account else None,
        account_match=finding.account_match.name.lower(),
        note=finding.note,
        spine_facts=[_to_fact_response(f) for f in finding.spine_facts],
        evidence_facts=[_to_fact_response(f) for f in finding.evidence_facts],
    )


def _to_fact_response(fact: FinancialFact) -> ReconciliationFactResponse:
    return ReconciliationFactResponse(
        source_id=fact.source_id,
        role=fact.role.value,
        reporter_tax_id=fact.reporter_tax_id.value,
        reporter_name=fact.reporter_name,
        concept_id=fact.concept_id,
        amount=str(fact.amount.amount),
        account=fact.account.raw if fact.account else None,
        detail=fact.detail,
        locator=fact.locator,
    )


def _to_mapping_response(mapping: ConceptMapping) -> ConceptMappingResponse:
    return ConceptMappingResponse(
        document_type_id=mapping.document_type_id,
        kind_id=mapping.kind_id,
        reporter_path=mapping.reporter_path,
        reporter_name_path=mapping.reporter_name_path,
        period_path=mapping.period_path,
        entries=[
            ConceptMappingEntryPayload(
                field_path=e.field_path,
                concept_id=e.concept_id,
                account_path=e.account_path,
                sign=e.sign,
            )
            for e in mapping.entries
        ],
    )
