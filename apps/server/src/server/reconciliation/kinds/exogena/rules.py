"""What the exogena claims, and which certificate figure has to back it.

Two kinds of rule live here and the split is the point.

Most comparisons are *derived* from the correspondence table in `concepts.py`:
one exogena concept, the certificate concept that means the same thing,
compared per reporting party or per account. That direction — every declared
correspondence gets a rule, automatically — is what makes the report
row-driven. Hand-writing each comparison was the previous model, and a
hand-written pack is always shorter than the DIAN's vocabulary: on a real 2025
report it left 17 of 40 rows stated but never validated.

What stays hand-written is what the derivation cannot say: a comparison scoped
to one reporting party, or one whose two sides are not the same concept on both
ends. Those remain curated against a real document pair and reviewed before
they exist, which they must be — an accountant signs a return on the strength
of them.
"""

from __future__ import annotations

from decimal import Decimal

from server.reconciliation.core.concepts import ConceptCatalog
from server.reconciliation.core.rules import (
    ReconciliationRule,
    RuleScope,
    Tolerance,
    terms,
)
from server.reconciliation.kinds.exogena.concepts import Correspondence, correspondences
from server.shared import Money, TaxId

BANCOLOMBIA = TaxId("890903938")

#: Components summed from several certificate lines drift further than a single
#: rounded figure does, so these comparisons get a wider absolute allowance.
_COMPONENT_SUM_TOLERANCE = Tolerance(absolute=Money.of(100), relative=Decimal("0.00001"))


def build_rules(catalog: ConceptCatalog) -> tuple[ReconciliationRule, ...]:
    """The rule pack, in evaluation order.

    Order is load-bearing and its direction is not arbitrary: a fact belongs to
    the first rule that claims it, so the curated exceptions must be evaluated
    before the derived defaults they are exceptions *to*. Reversed, the derived
    `dian:cuentas-por-pagar` rule would claim Bancolombia's debt row and check
    it against the certified loan capital alone, and the four-component sum
    that actually reconciles it would never run.
    """
    rules = (*_curated_rules(), *_derived_rules(catalog))
    _reject_conflicts(rules)
    return rules


def _curated_rules() -> tuple[ReconciliationRule, ...]:
    """The comparisons the correspondence table cannot express."""
    return (
        ReconciliationRule(
            id="exogena.cuentas_por_pagar.bancolombia",
            label="Cuentas por pagar contra el saldo de obligaciones certificado",
            reporter=BANCOLOMBIA,
            spine=terms("dian:cuentas-por-pagar"),
            # The exogena reports one debt figure; the certificate breaks the
            # same debt into loan capital, accrued interest, insurance and
            # other charges, and the credit card balance.
            evidence=terms(
                {
                    "bank:cert_cartera_capital",
                    "bank:cert_cartera_interes",
                    "bank:cert_cartera_otros",
                    "bank:cert_tarjeta_credito_capital",
                }
            ),
            scope=RuleScope.REPORTER,
            tolerance=_COMPONENT_SUM_TOLERANCE,
            note="The certificate splits into components what the exogena reports as one figure.",
        ),
    )


def _derived_rules(catalog: ConceptCatalog) -> tuple[ReconciliationRule, ...]:
    return tuple(_derive(c, catalog) for c in correspondences())


def _derive(correspondence: Correspondence, catalog: ConceptCatalog) -> ReconciliationRule:
    """One correspondence, read as the comparison it implies.

    Both sides become a single summed term, which is what the correspondence
    asserts: the concepts on one side are wordings of one figure, not
    components to be weighed against each other.
    """
    anchor = _anchor_concept(correspondence)
    return ReconciliationRule(
        id=correspondence.id or _rule_id_for(anchor),
        label=correspondence.label or catalog.label(anchor),
        spine=terms(correspondence.spine),
        evidence=terms(correspondence.evidence),
        scope=RuleScope.ACCOUNT if correspondence.per_account else RuleScope.REPORTER,
        note=correspondence.note,
    )


def _anchor_concept(correspondence: Correspondence) -> str:
    """The spine concept an unnamed correspondence takes its id and label from.

    Sorted rather than "the first one" because the table holds sets, so any
    other choice would make the rule id depend on set iteration order.
    """
    return sorted(correspondence.spine)[0]


def _rule_id_for(concept_id: str) -> str:
    return f"exogena.{concept_id.removeprefix('dian:').replace('-', '_')}"


def _reject_conflicts(rules: tuple[ReconciliationRule, ...]) -> None:
    """Fail at wiring time rather than silently shadowing a comparison.

    Two rules with one id make a finding impossible to trace back to what
    produced it. Two *derived* rules claiming one spine concept is worse: the
    later one would only ever see the facts the earlier one left behind, so a
    duplicated table entry would look like a rule that mysteriously never
    fires. Curated rules are exempt — overlapping a derived rule is exactly
    what makes them exceptions.
    """
    ids = [rule.id for rule in rules]
    duplicated_ids = sorted({i for i in ids if ids.count(i) > 1})
    if duplicated_ids:
        raise ValueError(f"Duplicate exogena rule id(s): {duplicated_ids}")

    claimed: set[str] = set()
    for correspondence in correspondences():
        clash = claimed & correspondence.spine
        if clash:
            raise ValueError(f"Spine concept(s) {sorted(clash)} appear in two correspondences")
        claimed |= correspondence.spine
