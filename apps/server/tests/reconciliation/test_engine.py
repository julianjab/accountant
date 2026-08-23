"""Engine behaviour on cases the real fixtures do not reach."""

from __future__ import annotations

from decimal import Decimal

import pytest

from server.reconciliation.core.concepts import Concept, ConceptCatalog
from server.reconciliation.core.engine import ReconciliationEngine
from server.reconciliation.core.findings import FindingStatus
from server.reconciliation.core.rules import (
    ReconciliationRule,
    RuleScope,
    Tolerance,
    minus,
    terms,
)
from server.shared import (
    AccountRef,
    FactRole,
    FinancialFact,
    MatchStrength,
    Money,
    Period,
    TaxId,
)

YEAR = Period.of_year(2025)
OTHER_YEAR = Period.of_year(2024)
BANK = TaxId("890903938")


class _Kind:
    """A minimal kind, so these tests exercise the engine and not the DIAN."""

    def __init__(self, rules: tuple[ReconciliationRule, ...]) -> None:
        self._rules = rules

    id = "test_kind"
    label = "Test"
    period_granularity = YEAR.granularity

    def concept_catalog(self) -> ConceptCatalog:
        return ConceptCatalog(
            [
                Concept("spine:a", "Spine A", FactRole.SPINE),
                Concept("spine:b", "Spine B", FactRole.SPINE),
                Concept("ev:a", "Evidence A", FactRole.EVIDENCE),
                Concept("ev:b", "Evidence B", FactRole.EVIDENCE),
            ]
        )

    def rules(self) -> tuple[ReconciliationRule, ...]:
        return self._rules

    def sources(self):
        return ()


def _fact(role, concept, amount, *, account=None, period=YEAR, source="s"):
    return FinancialFact(
        source_id=source,
        role=role,
        reporter_tax_id=BANK,
        reporter_name="Bank",
        subject_tax_id=None,
        concept_id=concept,
        period=period,
        amount=Money.of(amount),
        account=AccountRef(account) if account else None,
    )


def _spine(concept, amount, **kw):
    return _fact(FactRole.SPINE, concept, amount, **kw)


def _evidence(concept, amount, **kw):
    return _fact(FactRole.EVIDENCE, concept, amount, **kw)


def _rule(rule_id="r", scope=RuleScope.REPORTER, spine=("spine:a",), evidence=("ev:a",), **kw):
    return ReconciliationRule(
        id=rule_id, label=rule_id, spine=terms(*spine), evidence=terms(*evidence), scope=scope, **kw
    )


def _run(rules, facts):
    return ReconciliationEngine().reconcile(
        kind=_Kind(rules), client_id="c", period=YEAR, facts=facts, report_id="r"
    )


def test_a_difference_beyond_tolerance_is_a_mismatch():
    report = _run((_rule(),), [_spine("spine:a", 1000), _evidence("ev:a", 900)])
    finding = report.findings[0]
    assert finding.status is FindingStatus.MISMATCH
    assert finding.delta == Money.of(100)


def test_facts_from_another_period_are_ignored():
    """A 2024 certificate must not reconcile a 2025 claim."""
    report = _run(
        (_rule(),),
        [_spine("spine:a", 1000), _evidence("ev:a", 1000, period=OTHER_YEAR)],
    )
    assert report.findings[0].status is FindingStatus.MISSING_EVIDENCE


def test_the_first_rule_to_claim_a_fact_keeps_it():
    """Otherwise a figure would be checked twice and both totals would count
    it, inflating whichever side the overlap sits on."""
    specific = _rule("specific", reporter=BANK)
    general = _rule("general")
    report = _run((specific, general), [_spine("spine:a", 1000), _evidence("ev:a", 1000)])
    assert [f.rule_id for f in report.findings] == ["specific"]


def test_a_negative_term_subtracts_from_its_side():
    rule = ReconciliationRule(
        id="net",
        label="net",
        spine=terms("spine:a"),
        evidence=(*terms("ev:a"), *minus("ev:b")),
    )
    report = _run(
        (rule,), [_spine("spine:a", 700), _evidence("ev:a", 1000), _evidence("ev:b", 300)]
    )
    assert report.findings[0].status is FindingStatus.MATCHED


def test_a_weak_account_pairing_is_refused_when_the_amounts_disagree():
    """Card masks collide by construction, so the amounts are the second
    signal. Without them the engine would pair two unrelated cards and report
    a mismatch on each."""
    rule = _rule(scope=RuleScope.ACCOUNT)
    report = _run(
        (rule,),
        [_spine("spine:a", 1000, account="9383"), _evidence("ev:a", 55, account="4509129383")],
    )
    statuses = {f.status for f in report.findings}
    assert statuses == {FindingStatus.MISSING_EVIDENCE, FindingStatus.UNSUPPORTED_BY_SPINE}
    assert all(f.account_match is MatchStrength.NONE for f in report.findings)


def test_a_weak_account_pairing_is_accepted_when_the_amounts_corroborate_it():
    rule = _rule(scope=RuleScope.ACCOUNT)
    report = _run(
        (rule,),
        [_spine("spine:a", 1000, account="9383"), _evidence("ev:a", 1000, account="4509129383")],
    )
    assert len(report.findings) == 1
    assert report.findings[0].status is FindingStatus.MATCHED
    assert report.findings[0].account_match is MatchStrength.WEAK


def test_facts_without_an_account_never_pair_with_an_identified_account():
    rule = _rule(scope=RuleScope.ACCOUNT)
    report = _run((rule,), [_spine("spine:a", 1000), _evidence("ev:a", 1000, account="123456789")])
    assert {f.status for f in report.findings} == {
        FindingStatus.MISSING_EVIDENCE,
        FindingStatus.UNSUPPORTED_BY_SPINE,
    }


def test_a_relative_tolerance_scales_with_the_figures():
    rule = _rule(tolerance=Tolerance(absolute=Money.zero(), relative=Decimal("0.001")))
    report = _run((rule,), [_spine("spine:a", 1_000_000), _evidence("ev:a", 999_500)])
    assert report.findings[0].status is FindingStatus.MATCHED_WITHIN_TOLERANCE


def test_report_is_ordered_with_what_needs_attention_first():
    rules = (_rule("mismatch"), _rule("ok", spine=("spine:b",), evidence=("ev:b",)))
    report = _run(
        rules,
        [
            _spine("spine:a", 1000),
            _evidence("ev:a", 1),
            _spine("spine:b", 50),
            _evidence("ev:b", 50),
        ],
    )
    assert [f.status for f in report.findings][0] is FindingStatus.MISMATCH


def test_a_rule_may_not_count_the_same_concept_twice_on_one_side():
    with pytest.raises(ValueError, match="more than one"):
        ReconciliationRule(
            id="bad",
            label="bad",
            spine=terms("spine:a", "spine:a"),
            evidence=terms("ev:a"),
        )
