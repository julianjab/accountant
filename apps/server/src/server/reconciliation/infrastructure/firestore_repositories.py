"""Firestore-backed storage for reconciliation reports and concept mappings.

Two shape decisions worth stating, because neither is reversible cheaply once
reports exist:

Amounts are stored as strings. Firestore has no decimal type, and its number
type is a double — round-tripping 9,102,339.53 through a float is exactly the
kind of drift this engine exists to detect. A string preserves the figure the
report was computed from.

Findings live in a subcollection rather than an array on the report. A report
for one taxpayer already runs to dozens of findings, each carrying the facts
that back it, and a single document caps at 1 MiB; a subcollection also lets
the UI page through findings without loading the whole report.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from google.cloud.firestore import Client as FirestoreClient

from server.reconciliation.core.contribution import ContributionStatus, DocumentContribution
from server.reconciliation.core.findings import (
    FindingStatus,
    ReconciliationFinding,
    ReconciliationReport,
    ReportSummary,
    report_id_for,
)
from server.reconciliation.core.projection import ConceptMapping, ConceptMappingEntry
from server.shared import (
    AccountRef,
    FactRole,
    FinancialFact,
    MatchStrength,
    Money,
    Period,
    PeriodGranularity,
    TaxId,
)

REPORTS = "reconciliation_reports"
FINDINGS = "findings"
CONCEPT_MAPPINGS = "reconciliation_concept_mappings"


def _as_utc(value: datetime) -> datetime:
    """Firestore hands back its own tz-aware datetime subclass; normalize it."""
    return value.astimezone(UTC)


def _period_to_doc(period: Period) -> dict[str, Any]:
    return {
        "granularity": period.granularity.value,
        "year": period.year,
        "month": period.month,
    }


def _period_from_doc(data: dict[str, Any]) -> Period:
    return Period(
        granularity=PeriodGranularity(data["granularity"]),
        year=data["year"],
        month=data.get("month"),
    )


def _fact_to_doc(fact: FinancialFact) -> dict[str, Any]:
    return {
        "source_id": fact.source_id,
        "role": fact.role.value,
        "reporter_tax_id": fact.reporter_tax_id.value,
        "reporter_name": fact.reporter_name,
        "subject_tax_id": fact.subject_tax_id.value if fact.subject_tax_id else None,
        "concept_id": fact.concept_id,
        "period": _period_to_doc(fact.period),
        "amount": str(fact.amount.amount),
        "account": fact.account.raw if fact.account else None,
        "detail": fact.detail,
        "locator": fact.locator,
        "extras": dict(fact.extras),
    }


def _fact_from_doc(data: dict[str, Any]) -> FinancialFact:
    return FinancialFact(
        source_id=data["source_id"],
        role=FactRole(data["role"]),
        reporter_tax_id=TaxId(data["reporter_tax_id"]),
        reporter_name=data.get("reporter_name", ""),
        subject_tax_id=TaxId(data["subject_tax_id"]) if data.get("subject_tax_id") else None,
        concept_id=data["concept_id"],
        period=_period_from_doc(data["period"]),
        amount=Money(Decimal(data["amount"])),
        account=AccountRef(data["account"]) if data.get("account") else None,
        detail=data.get("detail", ""),
        locator=data.get("locator", ""),
        extras=data.get("extras") or {},
    )


def _finding_to_doc(finding: ReconciliationFinding, order: int) -> dict[str, Any]:
    return {
        # The engine orders findings by severity; Firestore does not preserve
        # insertion order, so the position is stored rather than recomputed.
        "order": order,
        # Kept alongside the document id, which is a sanitized form of it.
        "finding_id": finding.id,
        "status": finding.status.value,
        "rule_id": finding.rule_id,
        "label": finding.label,
        "reporter_tax_id": finding.reporter_tax_id.value,
        "reporter_name": finding.reporter_name,
        "spine_amount": str(finding.spine_amount.amount),
        "evidence_amount": str(finding.evidence_amount.amount),
        "delta": str(finding.delta.amount),
        "account": finding.account.raw if finding.account else None,
        "account_match": int(finding.account_match),
        "note": finding.note,
        "spine_facts": [_fact_to_doc(f) for f in finding.spine_facts],
        "evidence_facts": [_fact_to_doc(f) for f in finding.evidence_facts],
    }


def _finding_from_doc(data: dict[str, Any]) -> ReconciliationFinding:
    return ReconciliationFinding(
        id=data["finding_id"],
        status=FindingStatus(data["status"]),
        rule_id=data.get("rule_id"),
        label=data["label"],
        reporter_tax_id=TaxId(data["reporter_tax_id"]),
        reporter_name=data.get("reporter_name", ""),
        spine_amount=Money(Decimal(data["spine_amount"])),
        evidence_amount=Money(Decimal(data["evidence_amount"])),
        delta=Money(Decimal(data["delta"])),
        spine_facts=tuple(_fact_from_doc(f) for f in data.get("spine_facts", [])),
        evidence_facts=tuple(_fact_from_doc(f) for f in data.get("evidence_facts", [])),
        account=AccountRef(data["account"]) if data.get("account") else None,
        account_match=MatchStrength(data.get("account_match", 0)),
        note=data.get("note", ""),
    )


class FirestoreReconciliationReportRepository:
    def __init__(self, db: FirestoreClient) -> None:
        self._collection = db.collection(REPORTS)

    def save(self, report: ReconciliationReport) -> None:
        document = self._collection.document(report.id)
        document.set(
            {
                "client_id": report.client_id,
                "kind_id": report.kind_id,
                "period": _period_to_doc(report.period),
                "period_key": report.period.key,
                "generated_at": report.generated_at,
                "summary": {
                    "counts": {s.value: c for s, c in report.summary.counts.items()},
                    "total_findings": report.summary.total_findings,
                    "reconciled": report.summary.reconciled,
                    "needing_attention": report.summary.needing_attention,
                },
                "contributions": [
                    {
                        "document_id": c.document_id,
                        "file_name": c.file_name,
                        "status": c.status.value,
                        "fact_count": c.fact_count,
                        "detail": c.detail,
                    }
                    for c in report.contributions
                ],
            }
        )
        findings = document.collection(FINDINGS)
        written: set[str] = set()
        for order, finding in enumerate(report.findings):
            # Finding ids are derived from the rule and the parties, so a
            # rebuild overwrites the previous run's finding in place instead of
            # accumulating a second copy of it.
            document_id = _document_id(finding.id)
            findings.document(document_id).set(_finding_to_doc(finding, order))
            written.add(document_id)

        # A rebuild can also make a finding disappear: once the certificate for
        # a claim arrives, the MISSING_EVIDENCE line for it is replaced by a
        # matched one under a different id. Overwriting alone would leave the
        # old line in place, so the report would keep reporting a document as
        # missing after it was supplied.
        for snapshot in findings.list_documents():
            if snapshot.id not in written:
                snapshot.delete()

    def get(self, report_id: str) -> ReconciliationReport | None:
        snapshot = self._collection.document(report_id).get()
        if not snapshot.exists:
            return None
        return self._to_entity(snapshot.id, snapshot.to_dict())

    def get_latest(
        self, client_id: str, kind_id: str, period: Period
    ) -> ReconciliationReport | None:
        # A client and period have exactly one report, at a derived id, so this
        # is a point read: no query, no composite index, and nothing to scan.
        return self.get(report_id_for(client_id, kind_id, period))

    def _to_entity(self, doc_id: str, data: dict[str, Any]) -> ReconciliationReport:
        findings_query = self._collection.document(doc_id).collection(FINDINGS)
        documents = [s.to_dict() for s in findings_query.stream()]
        ordered = tuple(
            _finding_from_doc(d) for d in sorted(documents, key=lambda d: d.get("order", 0))
        )
        return ReconciliationReport(
            id=doc_id,
            client_id=data["client_id"],
            kind_id=data["kind_id"],
            period=_period_from_doc(data["period"]),
            generated_at=_as_utc(data["generated_at"]),
            findings=ordered,
            # Recomputed rather than read back: a stored summary that disagrees
            # with the findings beside it is worse than no summary at all.
            summary=ReportSummary.of(ordered),
            contributions=tuple(_contribution_from_doc(c) for c in data.get("contributions") or []),
        )


class FirestoreConceptMappingRepository:
    def __init__(self, db: FirestoreClient) -> None:
        self._collection = db.collection(CONCEPT_MAPPINGS)

    def save(self, mapping: ConceptMapping) -> None:
        self._collection.document(_mapping_id(mapping.document_type_id, mapping.kind_id)).set(
            {
                "document_type_id": mapping.document_type_id,
                "kind_id": mapping.kind_id,
                "reporter_path": mapping.reporter_path,
                "reporter_name_path": mapping.reporter_name_path,
                "period_path": mapping.period_path,
                "entries": [
                    {
                        "field_path": e.field_path,
                        "concept_id": e.concept_id,
                        "account_path": e.account_path,
                        "sign": e.sign,
                        "spine_concept_id": e.spine_concept_id,
                        "per_account": e.per_account,
                    }
                    for e in mapping.entries
                ],
            }
        )

    def get(self, document_type_id: str, kind_id: str) -> ConceptMapping | None:
        snapshot = self._collection.document(_mapping_id(document_type_id, kind_id)).get()
        return self._to_entity(snapshot.to_dict()) if snapshot.exists else None

    def list_for_kind(self, kind_id: str) -> list[ConceptMapping]:
        query = self._collection.where("kind_id", "==", kind_id)
        return [self._to_entity(s.to_dict()) for s in query.stream()]

    @staticmethod
    def _to_entity(data: dict[str, Any]) -> ConceptMapping:
        return ConceptMapping(
            document_type_id=data["document_type_id"],
            kind_id=data["kind_id"],
            reporter_path=data.get("reporter_path"),
            reporter_name_path=data.get("reporter_name_path"),
            period_path=data.get("period_path"),
            entries=tuple(_mapping_entry_from_doc(e) for e in data.get("entries", [])),
        )


def _contribution_from_doc(data: dict[str, Any]) -> DocumentContribution:
    """Reads one contribution, surviving a status this version does not know.

    Statuses are written by whichever server version ran the reconciliation.
    Letting an unrecognised one raise would make the entire report unreadable
    — findings and all — over a single descriptive field.
    """
    try:
        status = ContributionStatus(data["status"])
    except (KeyError, ValueError):
        status = ContributionStatus.NOT_READY
    return DocumentContribution(
        document_id=data.get("document_id", ""),
        file_name=data.get("file_name", ""),
        status=status,
        fact_count=data.get("fact_count", 0),
        detail=data.get("detail", ""),
    )


def _mapping_entry_from_doc(data: dict[str, Any]) -> ConceptMappingEntry:
    """Reads one entry, tolerating rows written before today's invariants.

    A row asking to compare per account without an account path predates the
    rule that the two belong together. Refusing it here would make the whole
    mapping unreadable — every other entry with it — over one field, so the
    comparison degrades to totals instead, which is what that row could ever
    actually do.
    """
    account_path = data.get("account_path")
    return ConceptMappingEntry(
        field_path=data["field_path"],
        concept_id=data["concept_id"],
        account_path=account_path,
        sign=data.get("sign", 1),
        spine_concept_id=data.get("spine_concept_id"),
        per_account=bool(data.get("per_account")) and account_path is not None,
    )


def _mapping_id(document_type_id: str, kind_id: str) -> str:
    return f"{document_type_id}__{kind_id}"


def _document_id(finding_id: str) -> str:
    """Finding ids carry `|` and `/` from rule ids and account numbers; a
    Firestore document id may not contain `/`."""
    return finding_id.replace("/", "_")
