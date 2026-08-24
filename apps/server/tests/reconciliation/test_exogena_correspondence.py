"""The correspondence table: what it covers, what it deliberately does not,
and the evaluation order that keeps a curated rule from being swallowed.

The certificate figures used here are synthetic — unlike `fixtures.py`, no real
form 220 backs them — so they prove wiring, not arithmetic against a document.
The hand-verified arithmetic stays in `test_exogena_reconciliation.py`.
"""

from __future__ import annotations

import fixtures
import pytest

from server.reconciliation.core.engine import ReconciliationEngine
from server.reconciliation.core.findings import FindingStatus
from server.reconciliation.core.kind import SourceContent
from server.reconciliation.core.projection import (
    ConceptMapping,
    ConceptMappingEntry,
    project_facts,
)
from server.reconciliation.kinds.exogena import ExogenaReconciliation
from server.reconciliation.kinds.exogena.concepts import (
    correspondences,
    unvalidated_spine_concepts,
)
from server.shared import (
    FactRole,
    FinancialFact,
    Money,
    Period,
    TaxId,
)

PERIOD = Period.of_year(2025)

#: What the employer's certificado de ingresos y retenciones would say about
#: the salary row of the exogena fixture, to the peso.
EMPLOYER_CERTIFICATE_FIELDS = {
    "empleador_nit": "900809691-1",
    "empleador_nombre": "LA HAUS S.A.S.",
    "pagos_salarios": "129,604,000",
}

EMPLOYER_MAPPING = ConceptMapping(
    document_type_id="type-certificado-ingresos",
    kind_id="exogena_dian",
    reporter_path="empleador_nit",
    reporter_name_path="empleador_nombre",
    entries=(ConceptMappingEntry("pagos_salarios", "payroll:cert_pagos_salarios"),),
)


@pytest.fixture
def kind() -> ExogenaReconciliation:
    return ExogenaReconciliation()


def _spine_facts(kind: ExogenaReconciliation):
    extractor = kind.sources()[0].extractor
    assert extractor is not None
    return extractor.extract(
        SourceContent(
            data=fixtures.exogena_workbook_bytes(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_name="exogena-2025.xlsx",
            source_id="doc-exogena",
        )
    )


def _reconcile(kind: ExogenaReconciliation, *facts):
    return ReconciliationEngine().reconcile(
        kind=kind,
        client_id="client-1",
        period=PERIOD,
        facts=facts,
        report_id="report-1",
    )


def _finding(report, rule_id: str, reporter: str):
    matches = [
        f for f in report.findings if f.rule_id == rule_id and f.reporter_tax_id == TaxId(reporter)
    ]
    assert len(matches) == 1, f"expected exactly one {rule_id} for {reporter}, got {matches}"
    return matches[0]


def test_every_spine_concept_is_either_paired_or_explicitly_unvalidated(kind):
    """The table has to stay exhaustive, or coverage silently rots.

    A new DIAN wording added to the catalog with neither a correspondence nor a
    stated reason is exactly the situation this work removed: a row nobody
    decided about. Forcing the decision is cheaper than rediscovering it on a
    client's report.
    """
    catalog = kind.concept_catalog()
    declared = {c for correspondence in correspondences() for c in correspondence.spine}
    unvalidated = {concept_id for concept_id, _ in unvalidated_spine_concepts()}

    assert not declared & unvalidated
    assert declared | unvalidated == {c.id for c in catalog.spine_concepts}
    assert all(reason for _, reason in unvalidated_spine_concepts())


def test_every_correspondence_names_concepts_the_catalog_knows(kind):
    catalog = kind.concept_catalog()
    for correspondence in correspondences():
        assert all(c in catalog for c in correspondence.spine), correspondence
        assert all(c in catalog for c in correspondence.evidence), correspondence


def test_curated_rules_are_evaluated_before_derived_ones(kind):
    """Order is the whole difference between the two paths coexisting and the
    general one eating the specific one."""
    ids = [rule.id for rule in kind.rules()]
    assert ids.index("exogena.cuentas_por_pagar.bancolombia") < ids.index(
        "exogena.cuentas_por_pagar"
    )


def test_the_general_debt_rule_does_not_swallow_the_bancolombia_one(kind):
    """The behavioural half of the ordering: Bancolombia's debt row must reach
    the four-component sum, and the derived rule must not also claim it."""
    report = _reconcile(kind, *_spine_facts(kind))
    claimed = _finding(report, "exogena.cuentas_por_pagar.bancolombia", fixtures.BANCOLOMBIA)
    assert claimed.spine_amount == Money.of("146231584")
    assert not [
        f
        for f in report.findings
        if f.rule_id == "exogena.cuentas_por_pagar"
        and f.reporter_tax_id == TaxId(fixtures.BANCOLOMBIA)
    ]


def test_a_payroll_row_that_was_out_of_scope_now_reconciles(kind):
    """The salary row: 129,604,000 stated, and now checked against the
    employer's certificate instead of reported as unvalidated."""
    evidence = project_facts(
        EMPLOYER_MAPPING,
        EMPLOYER_CERTIFICATE_FIELDS,
        source_id="doc-certificado-ingresos",
        period=PERIOD,
        locator="page 1",
    )
    report = _reconcile(kind, *_spine_facts(kind), *evidence)

    finding = _finding(report, "exogena.pagos_salarios", fixtures.EMPLOYER)
    assert finding.status is FindingStatus.MATCHED
    assert finding.spine_amount == Money.of("129604000")
    assert finding.delta.is_zero


def test_a_payroll_row_with_no_certificate_asks_for_the_document(kind):
    report = _reconcile(kind, *_spine_facts(kind))
    finding = _finding(report, "exogena.pagos_salarios", fixtures.EMPLOYER)
    assert finding.status is FindingStatus.MISSING_EVIDENCE
    assert TaxId(fixtures.EMPLOYER) in {f.reporter_tax_id for f in report.missing_documents}


def test_a_concept_with_no_correspondence_still_surfaces_as_out_of_scope(kind):
    """OUT_OF_SCOPE has to survive the derivation.

    The property valuation the exogena states is not something the reporting
    party certifies, so no correspondence claims it. It must still reach the
    accountant as "stated, not validated" rather than be quietly dropped.
    """
    valuation = FinancialFact(
        source_id="doc-exogena",
        role=FactRole.SPINE,
        reporter_tax_id=TaxId("899999061"),
        reporter_name="MUNICIPIO",
        subject_tax_id=TaxId(fixtures.TAXPAYER_TAX_ID),
        concept_id="dian:avaluo-catastral",
        period=PERIOD,
        amount=Money.of("380000000"),
        detail="Valor avalúo catastral",
        locator="row 99",
    )
    report = _reconcile(kind, valuation)

    out_of_scope = report.of_status(FindingStatus.OUT_OF_SCOPE)
    assert [f.label for f in out_of_scope] == ["Avalúo catastral"]
    assert out_of_scope[0].rule_id is None
    assert out_of_scope[0].spine_amount == Money.of("380000000")


def test_an_uncurated_wording_is_still_out_of_scope(kind):
    """A DIAN wording nobody has taught the catalog cannot have a
    correspondence, so the derivation must leave it alone."""
    unknown = FinancialFact(
        source_id="doc-exogena",
        role=FactRole.SPINE,
        reporter_tax_id=TaxId(fixtures.BANCOLOMBIA),
        reporter_name="BANCOLOMBIA S.A.",
        subject_tax_id=TaxId(fixtures.TAXPAYER_TAX_ID),
        concept_id="dian:x-algun-concepto-nuevo",
        period=PERIOD,
        amount=Money.of("1000"),
        detail="Algún concepto nuevo de la DIAN",
        locator="row 99",
    )
    report = _reconcile(kind, unknown)
    assert [f.status for f in report.findings] == [FindingStatus.OUT_OF_SCOPE]
