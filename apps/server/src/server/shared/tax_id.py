from __future__ import annotations

import re
from dataclasses import dataclass

_NON_DIGITS = re.compile(r"\D")


@dataclass(frozen=True, slots=True)
class TaxId:
    """A Colombian NIT or cedula, normalized for comparison.

    The same party is written differently by every source: the exogena prints
    `890903938`, a bank certificate prints `890903938-8` or `890.903.938`. The
    verification digit is derived from the rest, so dropping it loses nothing
    and makes the identifier comparable across sources.
    """

    value: str

    @classmethod
    def parse(cls, raw: str | int | float | None) -> TaxId | None:
        if raw is None:
            return None
        # A spreadsheet cell reaches us as a float, and stringifying one keeps
        # its decimal point: `890903938.0` must not read as `8909039380`.
        if isinstance(raw, float) and raw.is_integer():
            raw = int(raw)
        text = str(raw).strip()
        if not text:
            return None
        # `-8` is the verification digit, not part of the identifier.
        body = text.split("-", 1)[0]
        digits = _NON_DIGITS.sub("", body)
        return cls(digits) if digits else None

    def __str__(self) -> str:
        return self.value
