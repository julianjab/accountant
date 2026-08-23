from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from server.shared.account_ref import AccountRef
from server.shared.money import Money
from server.shared.period import Period
from server.shared.tax_id import TaxId

_NO_EXTRAS: Mapping[str, str] = MappingProxyType({})


class FactRole(StrEnum):
    """Which side of a reconciliation a fact argues for."""

    #: Comes from the document that declares what *should* exist — the exogena.
    SPINE = "spine"
    #: Comes from a document that evidences one of those claims — a bank
    #: certificate, an invoice, a statement.
    EVIDENCE = "evidence"


@dataclass(frozen=True, slots=True)
class FinancialFact:
    """One assertion: *this party says this amount, for this concept, on this
    account, in this period*.

    This is the entire contract between document extraction and reconciliation,
    and the reason a second reconciliation model can be added without touching
    the engine. It deliberately knows nothing about the DIAN: `concept_id` is an
    opaque string whose meaning is owned by a reconciliation kind's concept
    catalog. If a tax authority's vocabulary ever leaks into this module, the
    kinds stop being pluggable.
    """

    #: Identifies where this came from, for traceability back to the document.
    source_id: str
    role: FactRole
    #: The party asserting the amount (a bank, an employer, the taxpayer).
    reporter_tax_id: TaxId
    #: How that party names itself in the source, carried for display so the
    #: report never has to resolve an identifier against another store.
    reporter_name: str
    #: The party the assertion is about.
    subject_tax_id: TaxId | None
    concept_id: str
    period: Period
    amount: Money
    account: AccountRef | None = None
    #: Verbatim wording from the source, shown to the accountant as-is.
    detail: str = ""
    #: Where inside the source this sits (`row 37`, `page 1`), for the UI link.
    locator: str = ""
    extras: Mapping[str, str] = field(default=_NO_EXTRAS)
