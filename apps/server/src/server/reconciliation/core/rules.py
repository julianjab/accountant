from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from server.shared import Money, TaxId


class RuleScope(StrEnum):
    """How a rule groups facts before comparing them."""

    #: One comparison per reporting party. Use when the two sides disclose the
    #: same total at different levels of detail — the exogena lists a balance
    #: per account while the certificate prints one consolidated balance.
    REPORTER = "reporter"
    #: One comparison per account. Use when both sides identify the account and
    #: each must reconcile on its own.
    ACCOUNT = "account"


@dataclass(frozen=True, slots=True)
class Term:
    """A signed group of concepts summed into one side of a comparison."""

    concepts: frozenset[str]
    sign: int = 1

    def __post_init__(self) -> None:
        if self.sign not in (1, -1):
            raise ValueError("A term's sign must be +1 or -1")
        if not self.concepts:
            raise ValueError("A term needs at least one concept")


@dataclass(frozen=True, slots=True)
class Tolerance:
    """How far apart two sides may sit and still be considered equal.

    Both bounds are needed and for different reasons: the absolute one absorbs
    rounding, since the exogena reports whole pesos against certificates that
    carry cents; the relative one keeps that same allowance meaningful on
    figures in the hundreds of millions.
    """

    absolute: Money
    relative: Decimal = Decimal(0)

    def allowance_for(self, reference: Money) -> Money:
        relative_part = Money.of(abs(reference.amount) * self.relative)
        return max(self.absolute, relative_part)

    def accepts(self, delta: Money, reference: Money) -> bool:
        return delta.abs() <= self.allowance_for(reference)


#: Absorbs peso-level rounding on both sides of a comparison without hiding a
#: real discrepancy. Every observed exogena-vs-certificate delta on genuinely
#: matching figures fell under $1; component sums drift a little further.
DEFAULT_TOLERANCE = Tolerance(absolute=Money.of(10), relative=Decimal("0.0001"))


@dataclass(frozen=True, slots=True)
class ReconciliationRule:
    """One comparison the engine knows how to make.

    A rule is deliberately not an expression tree. Every real cross-check seen
    so far — one-to-one, several spine rows against one certificate line, one
    spine row against a sum of certificate components — is a signed sum on each
    side plus a grouping choice, and keeping it to that keeps rules readable by
    the accountant who has to trust them.
    """

    id: str
    label: str
    spine: tuple[Term, ...]
    evidence: tuple[Term, ...]
    scope: RuleScope = RuleScope.REPORTER
    tolerance: Tolerance = DEFAULT_TOLERANCE
    #: Restricts the rule to one reporting party. None means it applies to
    #: whoever reports these concepts, which is what surfaces a missing
    #: certificate from a bank nobody wrote a specific rule for.
    reporter: TaxId | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if not self.spine or not self.evidence:
            raise ValueError(f"Rule {self.id} needs concepts on both sides")
        # Overlapping terms on one side would count a fact twice and quietly
        # inflate that side of the comparison, so this is rejected outright
        # rather than left for whoever debugs the resulting mismatch.
        for side_name, side in (("spine", self.spine), ("evidence", self.evidence)):
            seen: set[str] = set()
            for term in side:
                clash = seen & term.concepts
                if clash:
                    raise ValueError(
                        f"Rule {self.id}: concept(s) {sorted(clash)} appear in more than "
                        f"one {side_name} term"
                    )
                seen |= term.concepts

    @property
    def spine_concepts(self) -> frozenset[str]:
        return frozenset().union(*(t.concepts for t in self.spine))

    @property
    def evidence_concepts(self) -> frozenset[str]:
        return frozenset().union(*(t.concepts for t in self.evidence))

    def applies_to_reporter(self, reporter: TaxId) -> bool:
        return self.reporter is None or self.reporter == reporter


def terms(*groups: str | Iterable[str]) -> tuple[Term, ...]:
    """Build a positive side from concept ids, one term per group."""
    return tuple(Term(frozenset([g] if isinstance(g, str) else g)) for g in groups)


def minus(*groups: str | Iterable[str]) -> tuple[Term, ...]:
    """Build a negative side, for rules where a component is subtracted."""
    return tuple(Term(frozenset([g] if isinstance(g, str) else g), sign=-1) for g in groups)


def spine_concepts_answered_by(
    rules: Iterable[ReconciliationRule],
) -> dict[str, frozenset[str]]:
    """Which claims each piece of evidence is declared to back.

    A rule is an assertion that its two sides mean the same thing, so the rule
    pack already answers "which line of the base report does this certified
    figure belong to" — for most concepts, with exactly one line. Asking the
    person configuring a document type to answer it again is asking them to
    re-derive a table that is already written down, from a list of thirty, once
    per row of a table.

    Derived from the rules rather than from a kind's own correspondence table
    so this stays kind-agnostic: any model that declares rules gets the same
    guidance without `core` learning what its concepts mean.
    """
    answered: dict[str, set[str]] = {}
    for rule in rules:
        spine = rule.spine_concepts
        for concept_id in rule.evidence_concepts:
            answered.setdefault(concept_id, set()).update(spine)
    return {concept_id: frozenset(spine) for concept_id, spine in answered.items()}
