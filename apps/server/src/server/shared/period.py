from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

_KEY = re.compile(r"^(\d{4})(?:-(\d{2}))?$")


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

    @classmethod
    def parse(cls, key: str) -> Period:
        """The inverse of `key`: `2025` or `2025-03`.

        Here rather than at each caller because a period that round-trips
        through a string is the normal case — it is what a URL carries, what a
        report is stored under, and what a parsed document reports about
        itself — and two hand-rolled parsers would eventually disagree.
        """
        match = _KEY.match(key)
        if match is None:
            raise ValueError(f"A period key must be `YYYY` or `YYYY-MM`, not {key!r}")
        year, month = int(match.group(1)), match.group(2)
        return cls.of_year(year) if month is None else cls.of_month(year, int(month))

    @property
    def key(self) -> str:
        return f"{self.year:04d}" if self.month is None else f"{self.year:04d}-{self.month:02d}"

    def __str__(self) -> str:
        return self.key
