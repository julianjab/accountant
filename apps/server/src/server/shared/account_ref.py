from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum

_NON_DIGITS = re.compile(r"\D")

# Below this, digits carry too little entropy to identify an account on their
# own: a 4-digit card mask matches by construction, a 5-digit suffix collides.
_MIN_SIGNIFICANT_DIGITS = 6

# A card is disclosed as its last four digits and nothing else.
_MASK_LENGTH = 4


class MatchStrength(IntEnum):
    """How much the engine may lean on an account pairing.

    Ordered so callers can write `strength >= MatchStrength.STRONG`.
    """

    NONE = 0
    #: Digits agree only after a lossy normalization. A pairing this weak is
    #: not trusted on its own — the engine pairs on it only when the amounts
    #: corroborate it (see `matching.pair_accounts`).
    WEAK = 1
    #: Digits agree under a normalization that cannot merge two real accounts.
    STRONG = 2
    #: The same digits.
    EXACT = 3


@dataclass(frozen=True, slots=True)
class AccountRef:
    """An account, card or contract number as some source printed it.

    Equality is the wrong tool here. The same Bancolombia investment account
    reaches us as `0006302947` from the exogena and `0006000302947` from the
    certificate, and a credit card only ever appears as a four-digit mask.
    So this holds the raw text and answers *how strongly* two references look
    like the same account, leaving the decision to the caller.
    """

    raw: str

    @classmethod
    def parse(cls, raw: str | int | None) -> AccountRef | None:
        if raw is None:
            return None
        text = str(raw).strip()
        return cls(text) if _NON_DIGITS.sub("", text) else None

    @property
    def digits(self) -> str:
        return _NON_DIGITS.sub("", self.raw)

    @property
    def significant(self) -> str:
        """Digits without leading zeros — a purely presentational prefix."""
        return self.digits.lstrip("0") or "0"

    @property
    def is_masked(self) -> bool:
        """True when this is a disclosure mask (a card's last four digits)."""
        return len(self.digits) <= _MASK_LENGTH

    def match(self, other: AccountRef) -> MatchStrength:
        mine, theirs = self.digits, other.digits
        if not mine or not theirs:
            return MatchStrength.NONE
        if mine == theirs:
            return MatchStrength.EXACT

        mine_sig, theirs_sig = self.significant, other.significant
        if mine_sig == theirs_sig:
            return MatchStrength.STRONG

        # One source truncates the other: `...058562` against `64729058562`.
        # Requiring both sides to stay above the entropy floor keeps this from
        # collapsing short account numbers into each other.
        shorter, longer = sorted((mine_sig, theirs_sig), key=len)
        if len(shorter) >= _MIN_SIGNIFICANT_DIGITS and longer.endswith(shorter):
            return MatchStrength.STRONG

        # Observed on Bancolombia investment accounts: the exogena drops an
        # interior run of zeros the certificate keeps (`0006` `000` `302947`
        # against `0006` `302947`). Removing every zero reconciles the two, but
        # it can also merge genuinely different accounts, so it never rates
        # higher than WEAK.
        mine_dense, theirs_dense = mine.replace("0", ""), theirs.replace("0", "")
        if mine_dense == theirs_dense and len(mine_dense) >= _MIN_SIGNIFICANT_DIGITS:
            return MatchStrength.WEAK

        # A card mask carries only four digits; that is all either side can
        # offer, and four digits are not evidence on their own.
        if (self.is_masked or other.is_masked) and mine[-_MASK_LENGTH:] == theirs[-_MASK_LENGTH:]:
            return MatchStrength.WEAK

        return MatchStrength.NONE

    def __str__(self) -> str:
        return self.raw
