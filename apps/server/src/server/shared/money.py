from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_CENTS = Decimal("0.01")


@dataclass(frozen=True, slots=True, order=True)
class Money:
    """An amount in the client's reporting currency (COP).

    Reconciliation compares figures that reach us at different precisions: the
    exogena rounds every value to the peso while a bank certificate keeps two
    decimals, so the engine must be able to hold both without the comparison
    itself introducing a difference. Decimal (never float) is what makes a
    delta of 0.17 mean 0.17.
    """

    amount: Decimal

    @classmethod
    def of(cls, value: Decimal | int | str) -> Money:
        return cls(Decimal(value).quantize(_CENTS, rounding=ROUND_HALF_UP))

    @classmethod
    def parse(cls, value: object) -> Money | None:
        amount = parse_amount(value)
        return None if amount is None else cls.of(amount)

    @classmethod
    def zero(cls) -> Money:
        return cls(Decimal("0.00"))

    def __add__(self, other: Money) -> Money:
        return Money(self.amount + other.amount)

    def __sub__(self, other: Money) -> Money:
        return Money(self.amount - other.amount)

    def __neg__(self) -> Money:
        return Money(-self.amount)

    def __mul__(self, factor: int) -> Money:
        return Money(self.amount * factor)

    @property
    def is_zero(self) -> bool:
        return self.amount == 0

    def abs(self) -> Money:
        return Money(abs(self.amount))

    def __str__(self) -> str:
        return f"{self.amount:,.2f}"


def parse_amount(value: object) -> Decimal | None:
    """Read an amount out of whatever a source hands us.

    Numbers reach the engine as spreadsheet cells (already numeric) and as OCR
    output (`"$ 2,241,275.17"`, `"143.944.539,00"`, `"(1.234)"`). Colombian
    documents use both separator conventions, sometimes in the same file, so
    the separator that appears last wins — it is the only one that can be the
    decimal point. Returns None when there is no number to read, which the
    caller treats as "this field was not reported", never as zero.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal | int | float):
        return Decimal(str(value))

    text = str(value).strip()
    if not text:
        return None

    negative = text.startswith("(") and text.endswith(")")
    cleaned = re.sub(r"[^\d,.\-]", "", text)
    if not cleaned or not re.search(r"\d", cleaned):
        return None
    negative = negative or cleaned.startswith("-")
    cleaned = cleaned.lstrip("-")

    last_comma, last_dot = cleaned.rfind(","), cleaned.rfind(".")
    if last_comma >= 0 and last_dot >= 0:
        decimal_at = max(last_comma, last_dot)
        integer = re.sub(r"\D", "", cleaned[:decimal_at])
        fraction = re.sub(r"\D", "", cleaned[decimal_at + 1 :])
    elif last_comma >= 0 or last_dot >= 0:
        decimal_at = max(last_comma, last_dot)
        tail = cleaned[decimal_at + 1 :]
        # A lone separator followed by exactly three digits is a thousands
        # group (`143.944`), not a fractional part.
        if len(tail) == 3 and cleaned.count(cleaned[decimal_at]) >= 1 and len(cleaned) > 4:
            integer, fraction = re.sub(r"\D", "", cleaned), ""
        else:
            integer = re.sub(r"\D", "", cleaned[:decimal_at])
            fraction = re.sub(r"\D", "", tail)
    else:
        integer, fraction = cleaned, ""

    amount = Decimal(f"{integer or '0'}.{fraction or '0'}")
    return -amount if negative else amount
