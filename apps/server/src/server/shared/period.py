from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PeriodGranularity(StrEnum):
    YEAR = "year"
    MONTH = "month"


@dataclass(frozen=True, slots=True, order=True)
class Period:
    """The window a reconciliation covers.

    Granularity is a property of the reconciliation kind, not of the platform:
    an exogena reconciliation is annual, a bank reconciliation is monthly. The
    kernel only needs both to be comparable and printable.
    """

    granularity: PeriodGranularity
    year: int
    month: int | None = None

    def __post_init__(self) -> None:
        if self.granularity is PeriodGranularity.MONTH and self.month is None:
            raise ValueError("A monthly period requires a month")
        if self.granularity is PeriodGranularity.YEAR and self.month is not None:
            raise ValueError("A yearly period must not carry a month")
        if self.month is not None and not 1 <= self.month <= 12:
            raise ValueError(f"Month out of range: {self.month}")

    @classmethod
    def of_year(cls, year: int) -> Period:
        return cls(PeriodGranularity.YEAR, year)

    @classmethod
    def of_month(cls, year: int, month: int) -> Period:
        return cls(PeriodGranularity.MONTH, year, month)

    @property
    def key(self) -> str:
        return f"{self.year:04d}" if self.month is None else f"{self.year:04d}-{self.month:02d}"

    def __str__(self) -> str:
        return self.key
