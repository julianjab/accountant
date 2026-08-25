"""The vocabulary and the plug point — the two things a second reconciliation
model has to go through."""

from __future__ import annotations

import pytest

from server.reconciliation.core.concepts import (
    Concept,
    ConceptCatalog,
    UnknownConcept,
)
from server.reconciliation.core.registry import KindRegistry, UnknownReconciliationKind
from server.reconciliation.kinds.exogena import KIND_ID, ExogenaReconciliation
from server.reconciliation.kinds.exogena.concepts import (
    concept_code_in,
    concept_id_for,
    normalize,
)
from server.shared import FactRole, PeriodGranularity


def _catalog() -> ConceptCatalog:
    return ConceptCatalog(
        [
            Concept("s:a", "Spine A", FactRole.SPINE),
            Concept("e:a", "Evidence A", FactRole.EVIDENCE),
        ]
    )


def test_a_catalog_separates_what_each_side_may_report():
    catalog = _catalog()
    assert len(catalog) == 2
    assert "s:a" in catalog
    assert [c.id for c in catalog.spine_concepts] == ["s:a"]
    assert [c.id for c in catalog.evidence_concepts] == ["e:a"]
    assert catalog.get("s:a").label == "Spine A"


def test_an_unknown_concept_still_renders_but_cannot_be_fetched():
    """Findings must stay printable for wordings nobody has curated yet."""
    catalog = _catalog()
    assert catalog.label("s:unseen") == "s:unseen"
    with pytest.raises(UnknownConcept):
        catalog.get("s:unseen")


def test_a_duplicate_concept_id_is_rejected():
    with pytest.raises(ValueError, match="Duplicate concept id"):
        ConceptCatalog([Concept("x", "A", FactRole.SPINE), Concept("x", "B", FactRole.SPINE)])


def test_catalogs_merge_so_kinds_can_share_a_vocabulary():
    merged = _catalog().merged_with(
        ConceptCatalog([Concept("e:b", "Evidence B", FactRole.EVIDENCE)])
    )
    assert len(merged) == 3


def test_the_registry_resolves_kinds_by_id():
    registry = KindRegistry([ExogenaReconciliation()])
    assert len(registry) == 1
    assert registry.get(KIND_ID).id == KIND_ID
    assert [k.id for k in registry.all()] == [KIND_ID]


def test_an_unregistered_kind_fails_loudly():
    with pytest.raises(UnknownReconciliationKind):
        KindRegistry().get("bank_statement")


def test_registering_the_same_kind_twice_is_rejected():
    registry = KindRegistry([ExogenaReconciliation()])
    with pytest.raises(ValueError, match="already registered"):
        registry.register(ExogenaReconciliation())


def test_the_exogena_kind_declares_a_spine_it_parses_and_evidence_it_does_not():
    kind = ExogenaReconciliation()
    assert kind.period_granularity is PeriodGranularity.YEAR
    assert kind.label
    spine, evidence = kind.sources()
    assert spine.role is FactRole.SPINE
    assert spine.extractor is not None and spine.required
    assert evidence.role is FactRole.EVIDENCE
    # Certificates vary by issuer, so they go through OCR, not a parser.
    assert evidence.extractor is None


def test_every_rule_only_names_concepts_the_catalog_knows():
    """A rule referring to a concept nobody emits would silently never fire."""
    kind = ExogenaReconciliation()
    catalog = kind.concept_catalog()
    for rule in kind.rules():
        assert all(c in catalog for c in rule.spine_concepts), rule.id
        assert all(c in catalog for c in rule.evidence_concepts), rule.id


def test_rule_ids_are_unique():
    ids = [r.id for r in ExogenaReconciliation().rules()]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize(
    ("detail", "expected"),
    [
        ("Pagos por salarios (Concepto: 2276)", "dian:pagos-salarios"),
        ("PAGOS POR SALARIOS", "dian:pagos-salarios"),
        (
            "Cesantías consignadas al fondo de cesantías (Concepto: 2276)",
            "dian:cesantias-consignadas",
        ),
        ("Saldo cuentas bancarias (Titular Principal)", "dian:saldo-cuentas-bancarias"),
    ],
)
def test_wordings_fold_onto_one_concept_regardless_of_accents_case_or_code(detail, expected):
    assert concept_id_for(detail) == expected


def test_the_dian_code_alone_never_decides_the_concept():
    """2276 covers salaries, severance, benefits, health contributions and AFC
    deposits. Indexing by it would sum five different things into one."""
    salaries = concept_id_for("Pagos por salarios (Concepto: 2276)")
    benefits = concept_id_for("Pagos por prestaciones sociales (Concepto: 2276)")
    assert salaries != benefits
    assert concept_code_in("Pagos por salarios (Concepto: 2276)") == "2276"
    assert concept_code_in("Total saldo a favor") == ""


def test_an_uncurated_wording_becomes_its_own_concept_rather_than_vanishing():
    concept_id = concept_id_for("Algún concepto nuevo de la DIAN (Concepto: 9999)")
    assert concept_id.startswith("dian:x-")
    assert "algun-concepto-nuevo" in concept_id


@pytest.mark.parametrize("detail", ["", "   ", "(Concepto: 1)"])
def test_an_empty_wording_still_yields_a_usable_concept(detail):
    assert concept_id_for(detail).startswith("dian:x-")
    assert normalize(detail) in ("", "")


# --- What a configuration screen can stop asking -----------------------------


def test_the_rules_say_which_claim_each_piece_of_evidence_backs():
    """The mapping screen asks two questions per figure, and the second one is
    already written down: a rule asserts that its two sides mean the same
    thing."""
    from server.reconciliation.core.rules import spine_concepts_answered_by
    from server.reconciliation.kinds.exogena import ExogenaReconciliation

    answered = spine_concepts_answered_by(ExogenaReconciliation().rules())

    assert answered["payroll:cert_pagos_salarios"] == frozenset({"dian:pagos-salarios"})
    # Severance is the case the screen must keep asking about: the same
    # certificate line answers either exogena wording.
    assert answered["payroll:cert_cesantias_consignadas"] == frozenset(
        {"dian:cesantias-abonadas", "dian:cesantias-consignadas"}
    )


def test_evidence_no_rule_covers_is_absent_rather_than_empty():
    """Absent means "nothing declared", which the screen says out loud. An
    empty set would read the same as "backs nothing", and the difference is
    whether the accountant is looking at a gap or at a decision."""
    from server.reconciliation.core.rules import (
        ReconciliationRule,
        Term,
        spine_concepts_answered_by,
    )

    rule = ReconciliationRule(
        id="r",
        label="R",
        spine=(Term(frozenset({"s:one"})),),
        evidence=(Term(frozenset({"e:one"})),),
    )

    answered = spine_concepts_answered_by([rule])

    assert answered == {"e:one": frozenset({"s:one"})}
    assert "e:two" not in answered


def test_evidence_named_by_two_rules_answers_both():
    from server.reconciliation.core.rules import (
        ReconciliationRule,
        Term,
        spine_concepts_answered_by,
    )

    rules = [
        ReconciliationRule(
            id=f"r{i}",
            label="R",
            spine=(Term(frozenset({f"s:{i}"})),),
            evidence=(Term(frozenset({"e:one"})),),
        )
        for i in (1, 2)
    ]

    assert spine_concepts_answered_by(rules) == {"e:one": frozenset({"s:1", "s:2"})}
