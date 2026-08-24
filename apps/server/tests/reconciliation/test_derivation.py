"""Turning what a person configured into rules the engine runs.

This is what makes a reconciliation correctable without a deploy, so the
cases below are the ones a misconfiguration would land on.
"""

from server.reconciliation.core.concepts import Concept, ConceptCatalog
from server.reconciliation.core.derivation import rules_from_mappings
from server.reconciliation.core.projection import ConceptMapping, ConceptMappingEntry
from server.reconciliation.core.rules import RuleScope
from server.shared import FactRole

CATALOG = ConceptCatalog(
    [
        Concept("dian:saldo", "Saldo cuentas bancarias", FactRole.SPINE),
        Concept("dian:deuda", "Cuentas por pagar", FactRole.SPINE),
        Concept("bank:saldo_ahorros", "Saldo de ahorros", FactRole.EVIDENCE),
        Concept("bank:capital", "Capital", FactRole.EVIDENCE),
        Concept("bank:interes", "Interés", FactRole.EVIDENCE),
        Concept("bank:tarjeta", "Tarjeta", FactRole.EVIDENCE),
    ]
)


def _mapping(*entries: ConceptMappingEntry, document_type_id: str = "t1") -> ConceptMapping:
    return ConceptMapping(
        document_type_id=document_type_id,
        kind_id="exogena_dian",
        reporter_path="nit",
        entries=entries,
    )


def _entry(field: str, concept: str, claim: str | None, per_account: bool = False):
    return ConceptMappingEntry(
        field_path=field, concept_id=concept, spine_concept_id=claim, per_account=per_account
    )


def test_a_configured_field_becomes_a_comparison():
    rules = rules_from_mappings(
        [_mapping(_entry("saldo", "bank:saldo_ahorros", "dian:saldo"))], CATALOG
    )

    assert len(rules) == 1
    assert rules[0].spine_concepts == frozenset({"dian:saldo"})
    assert rules[0].evidence_concepts == frozenset({"bank:saldo_ahorros"})
    assert rules[0].label == "Saldo cuentas bancarias"


def test_fields_answering_one_claim_are_summed():
    """The awkward case expressed without an expression editor: a debt the
    exogena states once and the certificate splits into components."""
    rules = rules_from_mappings(
        [
            _mapping(
                _entry("capital", "bank:capital", "dian:deuda"),
                _entry("interes", "bank:interes", "dian:deuda"),
                _entry("tarjeta", "bank:tarjeta", "dian:deuda"),
            )
        ],
        CATALOG,
    )

    assert len(rules) == 1
    assert rules[0].evidence_concepts == frozenset({"bank:capital", "bank:interes", "bank:tarjeta"})


def test_two_certificates_can_answer_the_same_claim():
    """Different issuers certify the same kind of figure on their own forms."""
    rules = rules_from_mappings(
        [
            _mapping(_entry("a", "bank:saldo_ahorros", "dian:saldo"), document_type_id="t1"),
            _mapping(_entry("b", "bank:capital", "dian:saldo"), document_type_id="t2"),
        ],
        CATALOG,
    )

    assert len(rules) == 1
    assert rules[0].evidence_concepts == frozenset({"bank:saldo_ahorros", "bank:capital"})


def test_account_scope_only_when_every_field_asks_for_it():
    """One field without an account means some evidence carries none, and
    scoping to accounts would leave it unmatched."""
    both = rules_from_mappings(
        [
            _mapping(
                _entry("a", "bank:capital", "dian:deuda", per_account=True),
                _entry("b", "bank:interes", "dian:deuda", per_account=True),
            )
        ],
        CATALOG,
    )
    mixed = rules_from_mappings(
        [
            _mapping(
                _entry("a", "bank:capital", "dian:deuda", per_account=True),
                _entry("b", "bank:interes", "dian:deuda", per_account=False),
            )
        ],
        CATALOG,
    )

    assert both[0].scope is RuleScope.ACCOUNT
    assert mixed[0].scope is RuleScope.REPORTER


def test_a_field_answering_nothing_produces_no_rule():
    """It is still extracted; it just is not compared against anything."""
    assert (
        rules_from_mappings([_mapping(_entry("saldo", "bank:saldo_ahorros", None))], CATALOG) == ()
    )


def test_concepts_the_catalog_does_not_know_are_ignored():
    """A mapping can outlive the vocabulary it was written against."""
    assert (
        rules_from_mappings(
            [
                _mapping(
                    _entry("a", "bank:saldo_ahorros", "dian:desaparecido"),
                    _entry("b", "bank:desaparecido", "dian:saldo"),
                )
            ],
            CATALOG,
        )
        == ()
    )


def test_no_mappings_means_no_rules():
    assert rules_from_mappings([], CATALOG) == ()
