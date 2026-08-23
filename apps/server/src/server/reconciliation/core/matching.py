from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from server.shared import AccountRef, MatchStrength


@dataclass(frozen=True, slots=True)
class AccountPairing:
    """One account bucket: a spine account, an evidence account, or both.

    `has_spine`/`has_evidence` say which sides the bucket draws from, and they
    are not inferable from the account fields: a bucket for facts that carry no
    account at all has `spine is None` while still drawing from the spine. Left
    to inference, the no-account bucket and an unpaired evidence account would
    both look like `spine is None` and would claim the same facts twice.
    """

    spine: AccountRef | None
    evidence: AccountRef | None
    strength: MatchStrength
    has_spine: bool
    has_evidence: bool

    @property
    def account(self) -> AccountRef | None:
        return self.spine if self.spine is not None else self.evidence


def pair_accounts(
    spine_accounts: Sequence[AccountRef | None],
    evidence_accounts: Sequence[AccountRef | None],
    corroborates: Callable[[AccountRef | None, AccountRef | None], bool],
) -> list[AccountPairing]:
    """Pair the accounts of two sides, leaving unmatched ones on their own.

    Pairing is greedy on match strength, which is safe because a stronger
    normalization can never merge two accounts a weaker one would separate.

    The rule that matters is what happens at MatchStrength.WEAK: those pairings
    come from lossy normalizations (a four-digit card mask, a collapsed run of
    interior zeros) and are accepted only when `corroborates` says the amounts
    agree. Without that second signal a wrong pairing would not just be wrong,
    it would manufacture a mismatch on two accounts that are each fine.
    """
    unpaired_spine = list(spine_accounts)
    unpaired_evidence = list(evidence_accounts)
    pairings: list[AccountPairing] = []

    # Facts with no account at all pair with each other and nothing else:
    # absence of an identifier is not evidence of a shared identity.
    if None in unpaired_spine and None in unpaired_evidence:
        unpaired_spine.remove(None)
        unpaired_evidence.remove(None)
        pairings.append(
            AccountPairing(None, None, MatchStrength.EXACT, has_spine=True, has_evidence=True)
        )

    candidates = [
        (spine.match(evidence), spine, evidence)
        for spine in unpaired_spine
        if spine is not None
        for evidence in unpaired_evidence
        if evidence is not None
    ]
    # Sort by strength, then by raw text so the outcome never depends on the
    # order facts happened to arrive in.
    candidates.sort(key=lambda c: (-c[0], c[1].raw, c[2].raw))

    for strength, spine, evidence in candidates:
        if strength is MatchStrength.NONE:
            break
        if spine not in unpaired_spine or evidence not in unpaired_evidence:
            continue
        if strength is MatchStrength.WEAK and not corroborates(spine, evidence):
            continue
        unpaired_spine.remove(spine)
        unpaired_evidence.remove(evidence)
        pairings.append(
            AccountPairing(spine, evidence, strength, has_spine=True, has_evidence=True)
        )

    pairings.extend(
        AccountPairing(spine, None, MatchStrength.NONE, has_spine=True, has_evidence=False)
        for spine in unpaired_spine
    )
    pairings.extend(
        AccountPairing(None, evidence, MatchStrength.NONE, has_spine=False, has_evidence=True)
        for evidence in unpaired_evidence
    )
    return pairings
