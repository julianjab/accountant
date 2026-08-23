"""Guard rails and edge branches of the engine's building blocks."""

from __future__ import annotations

import pytest

from server.reconciliation.core.findings import (
    FindingStatus,
    ReconciliationFinding,
    ReportSummary,
)
from server.reconciliation.core.matching import pair_accounts
from server.reconciliation.core.rules import (
    ReconciliationRule,
    Term,
    Tolerance,
    minus,
    terms,
)
from server.shared import AccountRef, MatchStrength, Money, TaxId


def _never(_spine, _evidence) -> bool:
    return False


def _always(_spine, _evidence) -> bool:
    return True


def test_facts_carrying_no_account_form_their_own_shared_bucket():
    """Two sides that both omit the account are talking about the same thing;
    an omission still must not match an identified account."""
    pairings = pair_accounts([None], [None], _never)
    assert len(pairings) == 1
    assert pairings[0].spine is None and pairings[0].evidence is None
    assert pairings[0].has_spine and pairings[0].has_evidence
    assert pairings[0].strength is MatchStrength.EXACT


def test_an_unmatched_account_on_either_side_gets_a_bucket_of_its_own():
    pairings = pair_accounts([AccountRef("111111111")], [AccountRef("222222222")], _never)
    assert len(pairings) == 2
    spine_only = next(p for p in pairings if p.has_spine and not p.has_evidence)
    evidence_only = next(p for p in pairings if p.has_evidence and not p.has_spine)
    assert spine_only.account.digits == "111111111"
    assert evidence_only.account.digits == "222222222"


def test_an_account_is_claimed_by_only_one_pairing():
    """Greedy pairing must not hand the same account to two buckets."""
    pairings = pair_accounts(
        [AccountRef("64729058562")],
        [AccountRef("64729058562"), AccountRef("729058562")],
        _always,
    )
    paired = [p for p in pairings if p.has_spine and p.has_evidence]
    assert len(paired) == 1
    assert paired[0].strength is MatchStrength.EXACT


def test_pairing_does_not_depend_on_the_order_facts_arrived_in():
    left = pair_accounts(
        [AccountRef("111111111"), AccountRef("222222222")],
        [AccountRef("222222222"), AccountRef("111111111")],
        _always,
    )
    right = pair_accounts(
        [AccountRef("222222222"), AccountRef("111111111")],
        [AccountRef("111111111"), AccountRef("222222222")],
        _always,
    )
    assert [(p.spine, p.evidence) for p in left] == [(p.spine, p.evidence) for p in right]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"sign": 0}, "sign must be"),
        ({"sign": 2}, "sign must be"),
    ],
)
def test_a_term_with_a_meaningless_sign_is_rejected(kwargs, message):
    with pytest.raises(ValueError, match=message):
        Term(frozenset({"x"}), **kwargs)


def test_an_empty_term_is_rejected():
    with pytest.raises(ValueError, match="at least one concept"):
        Term(frozenset())


def test_a_rule_missing_a_side_is_rejected():
    with pytest.raises(ValueError, match="both sides"):
        ReconciliationRule(id="r", label="r", spine=terms("a"), evidence=())


def test_a_rule_without_a_party_applies_to_everyone():
    rule = ReconciliationRule(id="r", label="r", spine=terms("a"), evidence=terms("b"))
    assert rule.applies_to_reporter(TaxId("890903938"))
    pinned = ReconciliationRule(
        id="r", label="r", spine=terms("a"), evidence=terms("b"), reporter=TaxId("890903938")
    )
    assert pinned.applies_to_reporter(TaxId("890903938"))
    assert not pinned.applies_to_reporter(TaxId("800150280"))


def test_a_rules_concept_sets_span_all_of_its_terms():
    rule = ReconciliationRule(
        id="r", label="r", spine=terms("a", "b"), evidence=(*terms("c"), *minus("d"))
    )
    assert rule.spine_concepts == frozenset({"a", "b"})
    assert rule.evidence_concepts == frozenset({"c", "d"})


def test_the_wider_of_the_two_tolerance_bounds_applies():
    tolerance = Tolerance(absolute=Money.of(10), relative=__import__("decimal").Decimal("0.01"))
    # On a small figure the absolute bound is the wider one.
    assert tolerance.allowance_for(Money.of(100)) == Money.of(10)
    # On a large one the relative bound overtakes it.
    assert tolerance.allowance_for(Money.of(100_000)) == Money.of(1000)
    assert tolerance.accepts(Money.of("-9.99"), Money.of(100))
    assert not tolerance.accepts(Money.of("10.01"), Money.of(100))


def _finding(status: FindingStatus) -> ReconciliationFinding:
    return ReconciliationFinding(
        id=f"f-{status}",
        status=status,
        rule_id=None,
        label="x",
        reporter_tax_id=TaxId("890903938"),
        reporter_name="Bank",
        spine_amount=Money.zero(),
        evidence_amount=Money.zero(),
        delta=Money.zero(),
        spine_facts=(),
        evidence_facts=(),
    )


def test_a_summary_accounts_for_every_status_including_the_absent_ones():
    findings = (
        _finding(FindingStatus.MATCHED),
        _finding(FindingStatus.MISMATCH),
        _finding(FindingStatus.OUT_OF_SCOPE),
    )
    summary = ReportSummary.of(findings)
    assert summary.total_findings == 3
    assert summary.reconciled == 1
    # Out of scope is neither reconciled nor actionable: it was not validated.
    assert summary.needing_attention == 1
    assert summary.counts[FindingStatus.MISSING_EVIDENCE] == 0
    assert set(summary.counts) == set(FindingStatus)


def test_a_finding_reports_whether_it_reconciled():
    assert _finding(FindingStatus.MATCHED_WITHIN_TOLERANCE).is_reconciled
    assert not _finding(FindingStatus.MISSING_EVIDENCE).is_reconciled


@pytest.mark.parametrize("raw", [None, "", "  ", "sin dígitos"])
def test_an_account_reference_with_no_digits_is_nothing(raw):
    assert AccountRef.parse(raw) is None


def test_an_account_reference_keeps_the_text_the_source_printed():
    account = AccountRef.parse(" 8704-1292758 ")
    assert str(account) == "8704-1292758"
    assert account.digits == "87041292758"
    assert not account.is_masked
    assert AccountRef("9383").is_masked


def test_an_account_with_no_digits_matches_nothing():
    assert AccountRef("n/a").match(AccountRef("64729058562")) is MatchStrength.NONE


def test_a_report_falls_back_to_an_empty_party_name_rather_than_failing():
    """Sources do not always name the party they identify by number."""
    from server.reconciliation.core.engine import ReconciliationEngine
    from server.reconciliation.core.rules import RuleScope
    from server.shared import FactRole, FinancialFact, Period

    year = Period.of_year(2025)
    rule = ReconciliationRule(
        id="r", label="r", spine=terms("s"), evidence=terms("e"), scope=RuleScope.REPORTER
    )

    class _Kind:
        id, label, period_granularity = "k", "K", year.granularity

        def concept_catalog(self):
            from server.reconciliation.core.concepts import ConceptCatalog

            return ConceptCatalog([])

        def rules(self):
            return (rule,)

        def sources(self):
            return ()

    def fact(role, concept, amount):
        return FinancialFact(
            source_id="s",
            role=role,
            reporter_tax_id=TaxId("890903938"),
            reporter_name="",
            subject_tax_id=None,
            concept_id=concept,
            period=year,
            amount=Money.of(amount),
        )

    report = ReconciliationEngine().reconcile(
        kind=_Kind(),
        client_id="c",
        period=year,
        facts=[fact(FactRole.SPINE, "s", 10), fact(FactRole.EVIDENCE, "e", 10)],
    )
    assert report.findings[0].reporter_name == ""
    # A catalog that has not been taught the concept still renders the finding.
    assert report.id
