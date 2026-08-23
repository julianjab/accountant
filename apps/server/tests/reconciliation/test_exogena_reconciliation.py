"""End-to-end: a real exogena report against two real bank certificates.

Every expected figure here was verified by hand against the source documents
before the engine existed, so a failure means the engine is wrong, not that the
expectation drifted.
"""

from __future__ import annotations

import fixtures
import pytest

from server.reconciliation.core.engine import ReconciliationEngine
from server.reconciliation.core.findings import FindingStatus
from server.reconciliation.core.kind import SourceContent
from server.reconciliation.core.projection import project_facts
from server.reconciliation.kinds.exogena import ExogenaReconciliation
from server.shared import MatchStrength, Money, Period, TaxId

PERIOD = Period.of_year(2025)


@pytest.fixture
def kind() -> ExogenaReconciliation:
    return ExogenaReconciliation()


@pytest.fixture
def report(kind: ExogenaReconciliation):
    extractor = kind.sources()[0].extractor
    assert extractor is not None
    spine = extractor.extract(
        SourceContent(
            data=fixtures.exogena_workbook_bytes(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_name="exogena-2025.xlsx",
            source_id="doc-exogena",
        )
    )
    evidence = (
        *project_facts(
            fixtures.FIDUCIARIA_MAPPING,
            fixtures.FIDUCIARIA_CERTIFICATE_FIELDS,
            source_id="doc-fiduciaria",
            period=PERIOD,
            locator="page 1",
        ),
        *project_facts(
            fixtures.BANCOLOMBIA_MAPPING,
            fixtures.BANCOLOMBIA_CERTIFICATE_FIELDS,
            source_id="doc-bancolombia",
            period=PERIOD,
            locator="page 1",
        ),
    )
    return ReconciliationEngine().reconcile(
        kind=kind,
        client_id="client-1",
        period=PERIOD,
        facts=(*spine, *evidence),
        report_id="report-1",
    )


def _finding(report, rule_id: str, reporter: str):
    matches = [
        f for f in report.findings if f.rule_id == rule_id and f.reporter_tax_id == TaxId(reporter)
    ]
    assert len(matches) == 1, f"expected exactly one {rule_id} for {reporter}, got {matches}"
    return matches[0]


def test_withholding_on_yields_reconciles_within_rounding(report):
    """Exogena 19,586 against a certificate that keeps cents: 19,586.35."""
    finding = _finding(report, "exogena.retencion_rendimientos", fixtures.FIDUCIARIA)
    assert finding.status is FindingStatus.MATCHED_WITHIN_TOLERANCE
    assert finding.spine_amount == Money.of("19586")
    assert finding.evidence_amount == Money.of("19586.35")
    assert finding.delta == Money.of("-0.35")


def test_yields_paid_reconciles(report):
    finding = _finding(report, "exogena.rendimientos_pagados", fixtures.FIDUCIARIA)
    assert finding.status is FindingStatus.MATCHED_WITHIN_TOLERANCE
    assert finding.evidence_amount == Money.of("347071.28")


def test_investment_balance_pairs_accounts_across_a_collapsed_zero_run(report):
    """`0006302947` and `0006000302947` are the same account.

    Neither leading-zero stripping nor suffix matching reconciles them, so the
    pairing rests on the lossy normalization — which the engine accepts only
    because the amounts corroborate it.
    """
    finding = _finding(report, "exogena.saldo_inversion_fic", fixtures.FIDUCIARIA)
    assert finding.status is FindingStatus.MATCHED_WITHIN_TOLERANCE
    assert finding.account_match is MatchStrength.WEAK
    assert finding.delta == Money.of("0.47")
    assert "partial identifier" in finding.note


def test_two_exogena_balances_reconcile_against_one_certified_balance(report):
    """2,135,378 + 105,897 against the certificate's consolidated 2,241,275.17."""
    finding = _finding(report, "exogena.saldo_cuentas_bancarias", fixtures.BANCOLOMBIA)
    assert finding.status is FindingStatus.MATCHED_WITHIN_TOLERANCE
    assert len(finding.spine_facts) == 2
    assert finding.spine_amount == Money.of("2241275")
    assert finding.evidence_amount == Money.of("2241275.17")


def test_one_exogena_debt_reconciles_against_summed_certificate_components(report):
    """146,231,584 against capital + interest + other charges + card balance."""
    finding = _finding(report, "exogena.cuentas_por_pagar.bancolombia", fixtures.BANCOLOMBIA)
    assert finding.status is FindingStatus.MATCHED_WITHIN_TOLERANCE
    assert len(finding.evidence_facts) == 4
    assert finding.evidence_amount == Money.of("146231575.50")
    assert finding.delta == Money.of("8.50")


@pytest.mark.parametrize(
    ("rule_id", "reporter"),
    [
        ("exogena.consumos_tarjeta", fixtures.DAVIBANK),
        ("exogena.consumos_tarjeta", fixtures.BANCOLOMBIA),
        ("exogena.rendimientos_pagados", fixtures.NU),
        ("exogena.inversiones_fic", fixtures.ALIANZA),
        ("exogena.cuentas_por_pagar", fixtures.CARDIF),
        ("exogena.cesantias_abonadas", fixtures.PROTECCION),
        ("exogena.aporte_afc", fixtures.BANCOLOMBIA),
    ],
)
def test_claims_with_no_certificate_are_reported_as_missing(report, rule_id, reporter):
    """The checklist of documents still to request from the client."""
    finding = _finding(report, rule_id, reporter)
    assert finding.status is FindingStatus.MISSING_EVIDENCE
    assert finding.evidence_amount.is_zero


def test_missing_documents_names_every_party_still_owed(report):
    owed = {f.reporter_tax_id.value for f in report.missing_documents}
    assert {
        fixtures.DAVIBANK,
        fixtures.NU,
        fixtures.ALIANZA,
        fixtures.CARDIF,
        fixtures.PROTECCION,
    } <= owed


def test_certified_figures_absent_from_the_exogena_are_surfaced(report):
    """Where unclaimed deductions live: the bank certifies it, the DIAN's
    report never mentions it."""
    unsupported = report.of_status(FindingStatus.UNSUPPORTED_BY_SPINE)
    concepts = {fact.concept_id for finding in unsupported for fact in finding.evidence_facts}
    assert "bank:cert_intereses_causados" in concepts
    assert "bank:cert_gmf_valor" in concepts

    interest = next(
        f
        for f in unsupported
        if any(x.concept_id == "bank:cert_intereses_causados" for x in f.evidence_facts)
    )
    assert interest.evidence_amount == Money.of("9946131")
    assert interest.spine_amount.is_zero


def test_unruled_exogena_rows_are_reported_as_unvalidated_not_as_clean(report):
    out_of_scope = report.of_status(FindingStatus.OUT_OF_SCOPE)
    labels = {f.label for f in out_of_scope}
    assert "Pagos por salarios" in labels
    assert all(f.rule_id is None for f in out_of_scope)


def test_nothing_is_double_counted_across_rules(report):
    """A fact may back at most one finding, or a figure would be checked twice
    and the totals would stop adding up."""
    seen: list[tuple[str, str, str]] = []
    for finding in report.findings:
        for fact in finding.spine_facts + finding.evidence_facts:
            seen.append((fact.source_id, fact.locator, fact.concept_id + str(fact.amount)))
    assert len(seen) == len(set(seen))


def test_summary_counts_every_finding_exactly_once(report):
    assert sum(report.summary.counts.values()) == len(report.findings)
    assert report.summary.total_findings == len(report.findings)
