"""What the exogena claims, and which certificate figure has to back it.

Each rule below was written against a real exogena/certificate pair and the
arithmetic verified before the rule existed. Rules are the asset of this
product: an accountant signs a return on the strength of them, so they are
curated by hand and reviewed, never generated.
"""

from __future__ import annotations

from decimal import Decimal

from server.reconciliation.core.rules import (
    ReconciliationRule,
    RuleScope,
    Tolerance,
    terms,
)
from server.shared import Money, TaxId

BANCOLOMBIA = TaxId("890903938")

#: Components summed from several certificate lines drift further than a single
#: rounded figure does, so these comparisons get a wider absolute allowance.
_COMPONENT_SUM_TOLERANCE = Tolerance(absolute=Money.of(100), relative=Decimal("0.00001"))


def build_rules() -> tuple[ReconciliationRule, ...]:
    """The rule pack, in evaluation order.

    Order is load-bearing: a fact belongs to the first rule that claims it, so
    party-specific rules must precede the general ones they would otherwise be
    swallowed by. The general rules are what turn a bank nobody wrote a rule
    for into a MISSING_EVIDENCE line instead of silence.
    """
    return (
        ReconciliationRule(
            id="exogena.cuentas_por_pagar.bancolombia",
            label="Cuentas por pagar contra el saldo de obligaciones certificado",
            reporter=BANCOLOMBIA,
            spine=terms("dian:cuentas-por-pagar"),
            # The exogena reports one debt figure; the certificate breaks the
            # same debt into loan capital, accrued interest, insurance and
            # other charges, and the credit card balance.
            evidence=terms(
                {
                    "bank:cert_cartera_capital",
                    "bank:cert_cartera_interes",
                    "bank:cert_cartera_otros",
                    "bank:cert_tarjeta_credito_capital",
                }
            ),
            scope=RuleScope.REPORTER,
            tolerance=_COMPONENT_SUM_TOLERANCE,
            note="The certificate splits into components what the exogena reports as one figure.",
        ),
        ReconciliationRule(
            id="exogena.saldo_cuentas_bancarias",
            label="Saldo de cuentas bancarias",
            spine=terms("dian:saldo-cuentas-bancarias"),
            evidence=terms("bank:cert_saldo_cuentas_ahorro"),
            # Scoped to the reporting party, not the account: the exogena
            # lists a balance per account while the certificate consolidates
            # them into a single disclosed balance.
            scope=RuleScope.REPORTER,
        ),
        ReconciliationRule(
            id="exogena.retencion_rendimientos",
            label="Retención practicada sobre rendimientos",
            spine=terms("dian:retencion-rendimientos"),
            evidence=terms("bank:cert_retencion_total"),
            scope=RuleScope.REPORTER,
        ),
        ReconciliationRule(
            id="exogena.rendimientos_pagados",
            label="Rendimientos e intereses pagados",
            spine=terms({"dian:rendimientos-pagados-fic", "dian:intereses-rendimientos-pagados"}),
            evidence=terms("bank:cert_rendimientos_pagados"),
            scope=RuleScope.REPORTER,
        ),
        ReconciliationRule(
            id="exogena.saldo_inversion_fic",
            label="Saldo de inversión en fondos de inversión colectiva",
            spine=terms("dian:saldo-inversion-fic"),
            evidence=terms("bank:cert_saldo_inversion"),
            scope=RuleScope.ACCOUNT,
        ),
        ReconciliationRule(
            id="exogena.inversiones_fic",
            label="Inversiones en fondos de inversión colectiva realizadas",
            spine=terms("dian:inversiones-fic"),
            evidence=terms("bank:cert_inversiones_fic"),
            scope=RuleScope.ACCOUNT,
        ),
        ReconciliationRule(
            id="exogena.consumos_tarjeta",
            label="Consumos con tarjeta de crédito o débito",
            spine=terms("dian:consumos-tarjeta"),
            evidence=terms("bank:cert_consumos_tarjeta"),
            # Cards are disclosed as a four-digit mask, so pairing here leans
            # on the amounts corroborating the account (see `pair_accounts`).
            scope=RuleScope.ACCOUNT,
        ),
        ReconciliationRule(
            id="exogena.movimientos_cuentas",
            label="Movimientos en cuentas corrientes y de ahorro",
            spine=terms("dian:movimientos-cuentas"),
            evidence=terms("bank:cert_movimientos_cuentas"),
            scope=RuleScope.ACCOUNT,
        ),
        ReconciliationRule(
            id="exogena.aporte_afc",
            label="Aportes a cuentas AFC",
            spine=terms({"dian:aporte-afc", "dian:aportes-afc-empleador"}),
            evidence=terms("bank:cert_aporte_afc"),
            scope=RuleScope.REPORTER,
        ),
        ReconciliationRule(
            id="exogena.cesantias_abonadas",
            label="Cesantías abonadas en el periodo",
            spine=terms({"dian:cesantias-abonadas", "dian:cesantias-consignadas"}),
            evidence=terms("bank:cert_cesantias_abonadas"),
            scope=RuleScope.REPORTER,
        ),
        ReconciliationRule(
            id="exogena.cuentas_por_pagar",
            label="Cuentas por pagar",
            spine=terms("dian:cuentas-por-pagar"),
            evidence=terms("bank:cert_cartera_capital"),
            scope=RuleScope.REPORTER,
            note="No party-specific rule applies; compared against the certified loan capital.",
        ),
    )
