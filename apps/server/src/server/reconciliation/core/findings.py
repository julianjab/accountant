from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from server.shared import AccountRef, FinancialFact, MatchStrength, Money, Period, TaxId


class FindingStatus(StrEnum):
    """The outcome of one comparison.

    The three non-matching outcomes are deliberately distinct: they send the
    accountant to three different places. A mismatch is a number to investigate,
    a missing document is something to request from the client, and an
    unsupported figure is usually a deduction the spine never mentioned.
    """

    MATCHED = "matched"
    MATCHED_WITHIN_TOLERANCE = "matched_within_tolerance"
    MISMATCH = "mismatch"
    #: The spine claims it; no document evidences it. Ask the client for it.
    MISSING_EVIDENCE = "missing_evidence"
    #: A document evidences it; the spine never mentions it.
    UNSUPPORTED_BY_SPINE = "unsupported_by_spine"
    #: The spine claims it and no rule knows how to check it. Not a defect —
    #: an honest statement that this figure was not validated.
    OUT_OF_SCOPE = "out_of_scope"

    @property
    def is_reconciled(self) -> bool:
        return self in (FindingStatus.MATCHED, FindingStatus.MATCHED_WITHIN_TOLERANCE)

    @property
    def needs_attention(self) -> bool:
        return self in (
            FindingStatus.MISMATCH,
            FindingStatus.MISSING_EVIDENCE,
            FindingStatus.UNSUPPORTED_BY_SPINE,
        )


@dataclass(frozen=True, slots=True)
class ReconciliationFinding:
    """One line of the report, carrying both sides and the facts behind them.

    The contributing facts travel with the finding on purpose: an accountant
    who cannot click from a delta back to the exogena row and the certificate
    page that produced it has no way to act on it.
    """

    id: str
    status: FindingStatus
    rule_id: str | None
    label: str
    reporter_tax_id: TaxId
    reporter_name: str
    spine_amount: Money
    evidence_amount: Money
    delta: Money
    spine_facts: tuple[FinancialFact, ...]
    evidence_facts: tuple[FinancialFact, ...]
    account: AccountRef | None = None
    account_match: MatchStrength = MatchStrength.NONE
    note: str = ""

    @property
    def is_reconciled(self) -> bool:
        return self.status.is_reconciled


@dataclass(frozen=True, slots=True)
class ReportSummary:
    counts: dict[FindingStatus, int]
    total_findings: int
    reconciled: int
    needing_attention: int

    @classmethod
    def of(cls, findings: tuple[ReconciliationFinding, ...]) -> ReportSummary:
        counts = Counter(f.status for f in findings)
        return cls(
            counts={status: counts.get(status, 0) for status in FindingStatus},
            total_findings=len(findings),
            reconciled=sum(1 for f in findings if f.status.is_reconciled),
            needing_attention=sum(1 for f in findings if f.status.needs_attention),
        )


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    id: str
    client_id: str
    kind_id: str
    period: Period
    generated_at: datetime
    findings: tuple[ReconciliationFinding, ...]
    summary: ReportSummary

    def of_status(self, *statuses: FindingStatus) -> tuple[ReconciliationFinding, ...]:
        wanted = set(statuses)
        return tuple(f for f in self.findings if f.status in wanted)

    @property
    def missing_documents(self) -> tuple[ReconciliationFinding, ...]:
        """What to request from the client, in the order the report found it."""
        return self.of_status(FindingStatus.MISSING_EVIDENCE)
