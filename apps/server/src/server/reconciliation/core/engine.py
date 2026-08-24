from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from server.reconciliation.core.concepts import ConceptCatalog
from server.reconciliation.core.contribution import DocumentContribution
from server.reconciliation.core.findings import (
    FindingStatus,
    ReconciliationFinding,
    ReconciliationReport,
    ReportSummary,
)
from server.reconciliation.core.kind import ReconciliationKind
from server.reconciliation.core.matching import pair_accounts
from server.reconciliation.core.rules import ReconciliationRule, RuleScope, Term
from server.shared import (
    AccountRef,
    FactRole,
    FinancialFact,
    MatchStrength,
    Money,
    Period,
    TaxId,
)

# Attention first: the report opens on what the accountant has to act on, and
# the figures that already reconcile sit underneath as corroboration.
_STATUS_ORDER = {
    FindingStatus.MISMATCH: 0,
    FindingStatus.MISSING_EVIDENCE: 1,
    FindingStatus.UNSUPPORTED_BY_SPINE: 2,
    FindingStatus.MATCHED_WITHIN_TOLERANCE: 3,
    FindingStatus.MATCHED: 4,
    FindingStatus.OUT_OF_SCOPE: 5,
}


@dataclass(frozen=True, slots=True)
class _Side:
    total: Money
    facts: tuple[FinancialFact, ...]

    @property
    def is_empty(self) -> bool:
        return not self.facts


class ReconciliationEngine:
    """Compares what the spine claims against what the documents evidence.

    Pure arithmetic over facts: no I/O, no AI, no knowledge of any particular
    reconciliation model. That is a correctness requirement, not an aesthetic
    one — a figure this engine reports has to be reproducible and explainable
    to a tax authority, which rules out a non-deterministic step anywhere in
    the path. A language model has a place either side of this class (reading
    documents before, wording explanations after) and no place inside it.
    """

    def reconcile(
        self,
        *,
        kind: ReconciliationKind,
        client_id: str,
        period: Period,
        facts: Iterable[FinancialFact],
        report_id: str | None = None,
        generated_at: datetime | None = None,
        contributions: tuple[DocumentContribution, ...] = (),
    ) -> ReconciliationReport:
        catalog = kind.concept_catalog()
        in_period = [f for f in facts if f.period == period]
        spine = [f for f in in_period if f.role is FactRole.SPINE]
        evidence = [f for f in in_period if f.role is FactRole.EVIDENCE]

        # A fact belongs to the first rule that claims it. Rules are evaluated
        # in the order the kind declares them, so a kind puts its specific
        # rules ahead of its catch-all ones and the outcome stays deterministic
        # regardless of the order facts arrived in.
        used_spine: set[int] = set()
        used_evidence: set[int] = set()

        findings: list[ReconciliationFinding] = []
        for rule in kind.rules():
            findings.extend(
                self._apply_rule(rule, catalog, spine, evidence, used_spine, used_evidence)
            )
        findings.extend(self._unclaimed(catalog, spine, used_spine, FactRole.SPINE))
        findings.extend(self._unclaimed(catalog, evidence, used_evidence, FactRole.EVIDENCE))

        ordered = tuple(
            sorted(
                findings,
                key=lambda f: (_STATUS_ORDER[f.status], f.reporter_name, f.label, f.id),
            )
        )
        return ReconciliationReport(
            id=report_id or str(uuid.uuid4()),
            client_id=client_id,
            kind_id=kind.id,
            period=period,
            generated_at=generated_at or datetime.now(UTC),
            findings=ordered,
            summary=ReportSummary.of(ordered),
            contributions=contributions,
        )

    def _apply_rule(
        self,
        rule: ReconciliationRule,
        catalog: ConceptCatalog,
        spine: Sequence[FinancialFact],
        evidence: Sequence[FinancialFact],
        used_spine: set[int],
        used_evidence: set[int],
    ) -> list[ReconciliationFinding]:
        spine_hits = _select(spine, used_spine, rule, rule.spine_concepts)
        evidence_hits = _select(evidence, used_evidence, rule, rule.evidence_concepts)
        if not spine_hits and not evidence_hits:
            return []

        findings: list[ReconciliationFinding] = []
        reporters = sorted(
            {f.reporter_tax_id for _, f in spine_hits}
            | {f.reporter_tax_id for _, f in evidence_hits},
            key=lambda t: t.value,
        )
        for reporter in reporters:
            mine_spine = [(i, f) for i, f in spine_hits if f.reporter_tax_id == reporter]
            mine_evidence = [(i, f) for i, f in evidence_hits if f.reporter_tax_id == reporter]
            if rule.scope is RuleScope.REPORTER:
                groups = [(None, MatchStrength.NONE, mine_spine, mine_evidence)]
            else:
                groups = self._group_by_account(rule, mine_spine, mine_evidence)

            for account, strength, group_spine, group_evidence in groups:
                if not group_spine and not group_evidence:
                    continue
                finding = self._evaluate(
                    rule, reporter, account, strength, group_spine, group_evidence
                )
                findings.append(finding)
                used_spine.update(i for i, _ in group_spine)
                used_evidence.update(i for i, _ in group_evidence)
        return findings

    def _group_by_account(
        self,
        rule: ReconciliationRule,
        spine_hits: list[tuple[int, FinancialFact]],
        evidence_hits: list[tuple[int, FinancialFact]],
    ) -> list[
        tuple[
            AccountRef | None,
            MatchStrength,
            list[tuple[int, FinancialFact]],
            list[tuple[int, FinancialFact]],
        ]
    ]:
        spine_accounts = _distinct_accounts(spine_hits)
        evidence_accounts = _distinct_accounts(evidence_hits)

        def corroborates(spine: AccountRef | None, evidence: AccountRef | None) -> bool:
            left = _sum_side([f for _, f in spine_hits if _same(f.account, spine)], rule.spine)
            right = _sum_side(
                [f for _, f in evidence_hits if _same(f.account, evidence)], rule.evidence
            )
            if left.is_empty or right.is_empty:
                return False
            delta = left.total - right.total
            reference = max(left.total.abs(), right.total.abs())
            return rule.tolerance.accepts(delta, reference)

        groups = []
        for pairing in pair_accounts(spine_accounts, evidence_accounts, corroborates):
            groups.append(
                (
                    pairing.account,
                    pairing.strength,
                    [(i, f) for i, f in spine_hits if _same(f.account, pairing.spine)]
                    if pairing.has_spine
                    else [],
                    [(i, f) for i, f in evidence_hits if _same(f.account, pairing.evidence)]
                    if pairing.has_evidence
                    else [],
                )
            )
        return groups

    def _evaluate(
        self,
        rule: ReconciliationRule,
        reporter: TaxId,
        account: AccountRef | None,
        strength: MatchStrength,
        spine_hits: list[tuple[int, FinancialFact]],
        evidence_hits: list[tuple[int, FinancialFact]],
    ) -> ReconciliationFinding:
        left = _sum_side([f for _, f in spine_hits], rule.spine)
        right = _sum_side([f for _, f in evidence_hits], rule.evidence)
        delta = left.total - right.total

        if left.is_empty:
            status, note = FindingStatus.UNSUPPORTED_BY_SPINE, rule.note
        elif right.is_empty:
            status, note = FindingStatus.MISSING_EVIDENCE, rule.note
        else:
            reference = max(left.total.abs(), right.total.abs())
            if delta.is_zero:
                status = FindingStatus.MATCHED
            elif rule.tolerance.accepts(delta, reference):
                status = FindingStatus.MATCHED_WITHIN_TOLERANCE
            else:
                status = FindingStatus.MISMATCH
            note = rule.note

        if strength is MatchStrength.WEAK:
            note = _join_notes(
                note,
                "Accounts paired on a partial identifier; the amounts corroborate the pairing.",
            )

        reporter_name = _reporter_name(spine_hits, evidence_hits)
        return ReconciliationFinding(
            id=f"{rule.id}|{reporter}|{account.digits if account else '-'}",
            status=status,
            rule_id=rule.id,
            label=rule.label,
            reporter_tax_id=reporter,
            reporter_name=reporter_name,
            spine_amount=left.total,
            evidence_amount=right.total,
            delta=delta,
            spine_facts=left.facts,
            evidence_facts=right.facts,
            account=account,
            account_match=strength,
            note=note,
        )

    def _unclaimed(
        self,
        catalog: ConceptCatalog,
        facts: Sequence[FinancialFact],
        used: set[int],
        role: FactRole,
    ) -> list[ReconciliationFinding]:
        """Report what no rule looked at, instead of letting it vanish.

        Silence here would be the worst failure mode the report has: a spine
        row nobody checked and a certificate figure nobody claimed would both
        read as "all clear". An unclaimed spine row is out of scope — stated,
        not validated. An unclaimed evidence figure is something the bank
        certifies that the spine never mentioned, which is where unclaimed
        deductions surface.
        """
        buckets: dict[tuple[str, str, str], list[FinancialFact]] = {}
        for index, fact in enumerate(facts):
            if index in used:
                continue
            key = (
                fact.reporter_tax_id.value,
                fact.concept_id,
                fact.account.digits if fact.account else "",
            )
            buckets.setdefault(key, []).append(fact)

        status = (
            FindingStatus.OUT_OF_SCOPE
            if role is FactRole.SPINE
            else FindingStatus.UNSUPPORTED_BY_SPINE
        )
        findings = []
        for (reporter, concept_id, account_digits), group in sorted(buckets.items()):
            total = Money.zero()
            for fact in group:
                total += fact.amount
            is_spine = role is FactRole.SPINE
            findings.append(
                ReconciliationFinding(
                    id=f"unclaimed|{role}|{concept_id}|{reporter}|{account_digits or '-'}",
                    status=status,
                    rule_id=None,
                    label=catalog.label(concept_id),
                    reporter_tax_id=TaxId(reporter),
                    reporter_name=group[0].reporter_name,
                    spine_amount=total if is_spine else Money.zero(),
                    evidence_amount=Money.zero() if is_spine else total,
                    delta=total if is_spine else -total,
                    spine_facts=tuple(group) if is_spine else (),
                    evidence_facts=() if is_spine else tuple(group),
                    account=group[0].account,
                    account_match=MatchStrength.NONE,
                    note=(
                        "No rule covers this concept, so it was not validated."
                        if is_spine
                        else "Reported by the document and absent from the spine."
                    ),
                )
            )
        return findings


def _select(
    facts: Sequence[FinancialFact],
    used: set[int],
    rule: ReconciliationRule,
    concepts: frozenset[str],
) -> list[tuple[int, FinancialFact]]:
    return [
        (i, f)
        for i, f in enumerate(facts)
        if i not in used
        and f.concept_id in concepts
        and rule.applies_to_reporter(f.reporter_tax_id)
    ]


def _sum_side(facts: Sequence[FinancialFact], side: tuple[Term, ...]) -> _Side:
    total = Money.zero()
    contributing: list[FinancialFact] = []
    for term in side:
        for fact in facts:
            if fact.concept_id in term.concepts:
                total += fact.amount * term.sign
                contributing.append(fact)
    return _Side(total=total, facts=tuple(contributing))


def _distinct_accounts(hits: Sequence[tuple[int, FinancialFact]]) -> list[AccountRef | None]:
    seen: list[AccountRef | None] = []
    for _, fact in hits:
        if not any(_same(fact.account, existing) for existing in seen):
            seen.append(fact.account)
    return seen


def _same(left: AccountRef | None, right: AccountRef | None) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return left.digits == right.digits


def _reporter_name(*groups: Sequence[tuple[int, FinancialFact]]) -> str:
    for group in groups:
        for _, fact in group:
            if fact.reporter_name:
                return fact.reporter_name
    return ""


def _join_notes(*parts: str) -> str:
    return " ".join(p for p in parts if p)
