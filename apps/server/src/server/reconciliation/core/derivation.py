from __future__ import annotations

from collections.abc import Iterable, Sequence

from server.reconciliation.core.concepts import ConceptCatalog
from server.reconciliation.core.projection import ConceptMapping
from server.reconciliation.core.rules import (
    ReconciliationRule,
    RuleScope,
    Term,
)

RULE_ID_PREFIX = "configured"


def rules_from_mappings(
    mappings: Iterable[ConceptMapping], catalog: ConceptCatalog
) -> tuple[ReconciliationRule, ...]:
    """Turns what someone configured into rules the engine can run.

    This is what lets a reconciliation be corrected without a deploy. A person
    reading a certificate says which claim of the exogena each of its fields
    answers; that statement is a comparison, and this assembles it.

    Fields answering the same claim are summed, which is how the awkward cases
    express themselves without an expression editor: a debt the exogena states
    once and the certificate splits into capital, interest, charges and card
    balance is four fields pointing at one claim.
    """
    by_claim: dict[str, tuple[set[str], list[bool]]] = {}
    for mapping in mappings:
        for entry in mapping.entries:
            claim = entry.spine_concept_id
            if claim is None or claim not in catalog or entry.concept_id not in catalog:
                continue
            evidence, scopes = by_claim.setdefault(claim, (set(), []))
            evidence.add(entry.concept_id)
            scopes.append(entry.per_account)

    return tuple(
        _rule_for(claim, evidence, scopes, catalog)
        for claim, (evidence, scopes) in sorted(by_claim.items())
        if evidence
    )


def _rule_for(
    claim: str, evidence: set[str], scopes: Sequence[bool], catalog: ConceptCatalog
) -> ReconciliationRule:
    return ReconciliationRule(
        id=f"{RULE_ID_PREFIX}.{claim}",
        label=catalog.label(claim),
        spine=(Term(frozenset({claim})),),
        evidence=(Term(frozenset(evidence)),),
        # Account-by-account only when every field answering this claim asks
        # for it. One that does not means some evidence carries no account, and
        # scoping to accounts would leave it unmatched.
        scope=RuleScope.ACCOUNT if scopes and all(scopes) else RuleScope.REPORTER,
        note="",
    )
