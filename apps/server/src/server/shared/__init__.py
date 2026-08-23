"""Kernel shared by every bounded context.

Value objects only: no I/O, no framework imports, and — critically — no
knowledge of any particular reconciliation model. Everything here must stay
true whether the model being reconciled is a DIAN exogena or a bank statement.
"""

from server.shared.account_ref import AccountRef, MatchStrength
from server.shared.financial_fact import FactRole, FinancialFact
from server.shared.money import Money
from server.shared.period import Period, PeriodGranularity
from server.shared.tax_id import TaxId

__all__ = [
    "AccountRef",
    "FactRole",
    "FinancialFact",
    "MatchStrength",
    "Money",
    "Period",
    "PeriodGranularity",
    "TaxId",
]
