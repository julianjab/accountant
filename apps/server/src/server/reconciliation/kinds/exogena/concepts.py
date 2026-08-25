"""The DIAN exogena's vocabulary, and the bank-certificate vocabulary it is
checked against.

Everything model-specific lives here. `reconciliation.core` never imports this
module; it only ever sees opaque concept ids.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from server.reconciliation.core.concepts import Concept, ConceptCatalog
from server.reconciliation.core.text import fold
from server.shared import FactRole

#: Trailing `(Concepto: 2276)` in an exogena detail. The code is kept as
#: metadata but never used as the concept identity: 2276 covers salaries,
#: severance, social benefits, health contributions and AFC deposits alike, so
#: two rows sharing a code are routinely different things.
CONCEPT_CODE = re.compile(r"\(\s*concepto\s*:\s*(\d+)\s*\)", re.IGNORECASE)

# Curated wordings, longest first so a specific one wins over a prefix of it.
# An unrecognized wording still becomes a concept (see `concept_id_for`) and
# still reaches the report as out of scope, which is how new DIAN wordings
# announce themselves instead of disappearing.
_SPINE_CONCEPTS: tuple[tuple[str, str, str], ...] = (
    ("pagos por salarios", "dian:pagos-salarios", "Pagos por salarios"),
    (
        "otros pagos rentas de trabajo y pension",
        "dian:otros-pagos-rentas-trabajo",
        "Otros pagos rentas de trabajo y pensión",
    ),
    (
        "pagos por prestaciones sociales",
        "dian:prestaciones-sociales",
        "Pagos por prestaciones sociales",
    ),
    (
        "retencion por pagos rentas de trabajo o pensiones",
        "dian:retencion-rentas-trabajo",
        "Retención por rentas de trabajo",
    ),
    (
        "retencion practicada rendimientos",
        "dian:retencion-rendimientos",
        "Retención practicada sobre rendimientos",
    ),
    (
        "cesantias consignadas al fondo de cesantias",
        "dian:cesantias-consignadas",
        "Cesantías consignadas al fondo",
    ),
    (
        "cesantias e intereses de cesantias pagadas al empleado",
        "dian:cesantias-pagadas",
        "Cesantías e intereses pagados al empleado",
    ),
    (
        "valor total de las cesantias abonadas en el periodo",
        "dian:cesantias-abonadas",
        "Cesantías abonadas en el periodo",
    ),
    (
        "aportes obligatorios a salud a cargo trabajador",
        "dian:aportes-salud",
        "Aportes obligatorios a salud",
    ),
    (
        "aporte obligatorio fondos pensiones y solidaridad",
        "dian:aportes-pension",
        "Aportes obligatorios a pensión",
    ),
    ("aportes a cuentas afc", "dian:aportes-afc-empleador", "Aportes a cuentas AFC"),
    (
        "aporte cuentas de ahorro para el fomento de la construccion",
        "dian:aporte-afc",
        "Aporte AFC (entidad financiera)",
    ),
    ("cuentas por pagar de clientes", "dian:cuentas-por-pagar", "Cuentas por pagar"),
    ("cuentas por cobrar", "dian:cuentas-por-cobrar", "Cuentas por cobrar"),
    ("total consumos o gastos con tarjeta", "dian:consumos-tarjeta", "Consumos con tarjeta"),
    (
        "valor total de los movimientos en cuentas corrientes y de ahorro",
        "dian:movimientos-cuentas",
        "Movimientos en cuentas",
    ),
    ("saldo cuentas bancarias", "dian:saldo-cuentas-bancarias", "Saldo de cuentas bancarias"),
    (
        "ahorro voluntario saldo final",
        "dian:ahorro-voluntario-saldo",
        "Ahorro voluntario, saldo final",
    ),
    (
        "cartera colectiva rendimientos pagados",
        "dian:rendimientos-pagados-fic",
        "Rendimientos pagados por FIC",
    ),
    (
        "intereses y rendimientos financieros pagados",
        "dian:intereses-rendimientos-pagados",
        "Intereses y rendimientos pagados",
    ),
    (
        "inversiones en fondos de inversion colectiva realizadas",
        "dian:inversiones-fic",
        "Inversiones en FIC realizadas",
    ),
    (
        "saldo inversion en fondos de inversion colectiva",
        "dian:saldo-inversion-fic",
        "Saldo de inversión en FIC",
    ),
    (
        "valor total de la inversion, aporte o derecho social",
        "dian:inversion-aporte-social",
        "Inversión, aporte o derecho social",
    ),
    ("valor avaluo catastral", "dian:avaluo-catastral", "Avalúo catastral"),
    ("valor avaluo vehiculo", "dian:avaluo-vehiculo", "Avalúo de vehículo"),
    (
        "monto total de facturacion electronica",
        "dian:facturacion-electronica",
        "Facturación electrónica con beneficio",
    ),
    (
        "suma valor total facturas tras ajustes por notas",
        "dian:facturas-ajustadas",
        "Facturas tras ajustes por notas",
    ),
    ("valor ingreso laboral promedio", "dian:ingreso-laboral-promedio", "Ingreso laboral promedio"),
    (
        "total patrimonio bruto declarado en el ano anterior",
        "dian:patrimonio-bruto-anterior",
        "Patrimonio bruto del año anterior",
    ),
    ("total saldo a favor", "dian:saldo-a-favor", "Saldo a favor"),
)

_EVIDENCE_CONCEPTS: tuple[tuple[str, str], ...] = (
    ("bank:cert_retencion_total", "Total retención practicada (certificado)"),
    ("bank:cert_rendimientos_pagados", "Rendimientos pagados (certificado)"),
    ("bank:cert_rendimientos_causados", "Rendimientos causados (certificado)"),
    ("bank:cert_base_gravable_retencion", "Base gravable de retención (certificado)"),
    ("bank:cert_saldo_inversion", "Saldo de la cuenta de inversión (certificado)"),
    ("bank:cert_saldo_cuentas_ahorro", "Saldo de cuentas de ahorro (certificado)"),
    ("bank:cert_cartera_capital", "Saldo de cartera, capital (certificado)"),
    ("bank:cert_cartera_interes", "Saldo de cartera, interés (certificado)"),
    ("bank:cert_cartera_otros", "Saldo de cartera, otros conceptos (certificado)"),
    ("bank:cert_tarjeta_credito_capital", "Saldo de tarjeta de crédito (certificado)"),
    ("bank:cert_consumos_tarjeta", "Consumos con tarjeta (certificado)"),
    ("bank:cert_movimientos_cuentas", "Movimientos en cuentas (certificado)"),
    ("bank:cert_inversiones_fic", "Inversiones en FIC (certificado)"),
    ("bank:cert_aporte_afc", "Aporte AFC (certificado)"),
    ("bank:cert_cesantias_abonadas", "Cesantías abonadas (certificado)"),
    ("bank:cert_gmf_base", "Base gravable del GMF (certificado)"),
    ("bank:cert_gmf_valor", "GMF retenido (certificado)"),
    ("bank:cert_intereses_causados", "Intereses causados de cartera (certificado)"),
    ("bank:cert_componente_inflacionario", "Componente inflacionario (certificado)"),
    # The employer's certificado de ingresos y retenciones (DIAN form 220).
    # Its boxes are fixed by resolution, so a payroll row of the exogena and a
    # box of the form either denote the same figure or they plainly do not —
    # there is no judgement call left to make when pairing them below.
    ("payroll:cert_pagos_salarios", "Pagos por salarios (certificado)"),
    ("payroll:cert_otros_pagos", "Otros pagos (certificado)"),
    ("payroll:cert_prestaciones_sociales", "Pagos por prestaciones sociales (certificado)"),
    ("payroll:cert_cesantias_pagadas", "Cesantías e intereses pagados al empleado (certificado)"),
    ("payroll:cert_cesantias_consignadas", "Cesantías consignadas al fondo (certificado)"),
    ("payroll:cert_aportes_salud", "Aportes obligatorios a salud (certificado)"),
    ("payroll:cert_aportes_pension", "Aportes obligatorios a pensión (certificado)"),
    ("payroll:cert_aportes_afc", "Aportes a cuentas AFC/AVC (certificado)"),
    ("payroll:cert_retencion_rentas_trabajo", "Retención por rentas de trabajo (certificado)"),
    # Two documents no document type maps onto yet. Declaring the concept
    # anyway is what makes the exogena row reach the accountant as "certificate
    # still to be requested" rather than as silence; the day one of these
    # certificates is onboarded, the mapping is all that has to be added.
    ("fund:cert_saldo_ahorro_voluntario", "Saldo de ahorro voluntario (certificado)"),
    ("equity:cert_valor_aporte_social", "Valor del aporte o derecho social (certificado)"),
)


@dataclass(frozen=True, slots=True)
class Correspondence:
    """Which certificate figure evidences a DIAN exogena concept.

    This table, not the rule pack, is what makes the report row-driven: every
    exogena row the parser recognizes gets *attempted* against the certificates
    on hand. Rules used to be the only path, and a hand-written pack is always
    shorter than the DIAN's vocabulary — on a real 2025 report that left 17 of
    40 rows stated but never validated. Declaring the pairing as data and
    deriving the rule from it (`rules.build_rules`) makes covering one more
    concept a one-line change, and makes what is *not* covered visible.

    A correspondence is an assertion that the two sides mean the same thing.
    Nothing weaker belongs here: an unvalidated row is honest, whereas two
    unrelated figures reconciling against each other is a wrong answer the
    accountant has no way to catch.
    """

    spine: frozenset[str]
    evidence: frozenset[str]
    #: True when both sides break the figure down by account and each account
    #: must reconcile on its own. False — the default — when the certificate
    #: consolidates what the exogena lists account by account, as banks do with
    #: savings balances; comparing those per account would report mismatches
    #: that are only a difference in disclosure detail.
    per_account: bool = False
    #: Only needed when one comparison covers several spine concepts, since the
    #: id and the label can then not be derived from a single one of them.
    id: str | None = None
    label: str | None = None
    note: str = ""


def _pair(
    spine: str | Iterable[str],
    evidence: str | Iterable[str],
    *,
    per_account: bool = False,
    rule_id: str | None = None,
    label: str | None = None,
    note: str = "",
) -> Correspondence:
    return Correspondence(
        spine=_as_set(spine),
        evidence=_as_set(evidence),
        per_account=per_account,
        id=rule_id,
        label=label,
        note=note,
    )


def _as_set(value: str | Iterable[str]) -> frozenset[str]:
    return frozenset([value] if isinstance(value, str) else value)


_CORRESPONDENCES: tuple[Correspondence, ...] = (
    # --- Bank and fiduciary certificates ---
    _pair("dian:retencion-rendimientos", "bank:cert_retencion_total"),
    _pair(
        {"dian:rendimientos-pagados-fic", "dian:intereses-rendimientos-pagados"},
        "bank:cert_rendimientos_pagados",
        # One certificate line answers both wordings: whether the payer calls
        # it a yield or an interest is a matter of the product it was earned
        # on, and no certificate splits its total that way.
        rule_id="exogena.rendimientos_pagados",
        label="Rendimientos e intereses pagados",
    ),
    _pair("dian:saldo-cuentas-bancarias", "bank:cert_saldo_cuentas_ahorro"),
    _pair("dian:saldo-inversion-fic", "bank:cert_saldo_inversion", per_account=True),
    _pair("dian:inversiones-fic", "bank:cert_inversiones_fic", per_account=True),
    # Cards are disclosed as a four-digit mask, so pairing here leans on the
    # amounts corroborating the account (see `core.matching.pair_accounts`).
    _pair("dian:consumos-tarjeta", "bank:cert_consumos_tarjeta", per_account=True),
    _pair("dian:movimientos-cuentas", "bank:cert_movimientos_cuentas", per_account=True),
    _pair(
        {"dian:aporte-afc", "dian:aportes-afc-empleador"},
        {"bank:cert_aporte_afc", "payroll:cert_aportes_afc"},
        # The same deposit is reported by the bank that received it and by the
        # employer that withheld it, and certified by whichever of the two
        # issued a document. Scoped per reporter, so the two never add up.
        rule_id="exogena.aporte_afc",
        label="Aportes a cuentas AFC",
    ),
    _pair(
        {"dian:cesantias-abonadas", "dian:cesantias-consignadas"},
        {"bank:cert_cesantias_abonadas", "payroll:cert_cesantias_consignadas"},
        rule_id="exogena.cesantias_abonadas",
        label="Cesantías abonadas en el periodo",
    ),
    _pair(
        "dian:cuentas-por-pagar",
        "bank:cert_cartera_capital",
        note="No party-specific rule applies; compared against the certified loan capital.",
    ),
    # --- The employer's certificado de ingresos y retenciones (form 220) ---
    # Box for box. These rows dominate a salaried taxpayer's exogena and not
    # one of them was being checked before this table existed.
    _pair("dian:pagos-salarios", "payroll:cert_pagos_salarios"),
    _pair("dian:otros-pagos-rentas-trabajo", "payroll:cert_otros_pagos"),
    _pair("dian:prestaciones-sociales", "payroll:cert_prestaciones_sociales"),
    _pair("dian:cesantias-pagadas", "payroll:cert_cesantias_pagadas"),
    _pair("dian:aportes-salud", "payroll:cert_aportes_salud"),
    _pair("dian:aportes-pension", "payroll:cert_aportes_pension"),
    _pair("dian:retencion-rentas-trabajo", "payroll:cert_retencion_rentas_trabajo"),
    # --- Certificates not onboarded yet, declared so the row gets requested ---
    _pair("dian:ahorro-voluntario-saldo", "fund:cert_saldo_ahorro_voluntario"),
    _pair("dian:inversion-aporte-social", "equity:cert_valor_aporte_social"),
)

#: Spine concepts left deliberately unchecked, and why. They surface as
#: OUT_OF_SCOPE, which is not a defect: "stated, not validated" is an answer
#: the accountant can act on, whereas inventing a correspondence to make the
#: line disappear would trade it for a comparison nobody can trust. Every
#: reason below is either "no single party certifies this figure" or "the
#: exogena does not say enough to know which certified figure it is".
_UNVALIDATED: tuple[tuple[str, str], ...] = (
    (
        "dian:cuentas-por-cobrar",
        "The exogena does not say which side of the relationship the balance "
        "sits on, so pairing it with a certified loan capital could compare a "
        "debt against a credit.",
    ),
    (
        "dian:avaluo-catastral",
        "Assessed by the municipality on the property tax bill, not certified "
        "to the taxpayer by the party that reported it.",
    ),
    (
        "dian:avaluo-vehiculo",
        "Assessed by the transit authority, not certified to the taxpayer by "
        "the party that reported it.",
    ),
    (
        "dian:facturacion-electronica",
        "Aggregated by the DIAN across every issuer, so no one document certifies the total.",
    ),
    (
        "dian:facturas-ajustadas",
        "The same aggregate after credit and debit notes; still no single issuer to certify it.",
    ),
    (
        "dian:ingreso-laboral-promedio",
        "Computed by the DIAN from the payroll it received; no issuer certifies an average.",
    ),
    (
        "dian:patrimonio-bruto-anterior",
        "Carried over from the taxpayer's own prior return, which is not third-party evidence.",
    ),
    (
        "dian:saldo-a-favor",
        "Determined in the taxpayer's own prior return, which is not third-party evidence.",
    ),
)


def correspondences() -> tuple[Correspondence, ...]:
    """The declared spine → evidence pairings, in reporting order."""
    return _CORRESPONDENCES


def unvalidated_spine_concepts() -> tuple[tuple[str, str], ...]:
    """Spine concepts with no correspondence, each with the reason it has none."""
    return _UNVALIDATED


UNCURATED_PREFIX = "dian:x-"


def normalize(text: str) -> str:
    """Fold a detail wording down to something matchable.

    The shared folding — accents, casing, spacing — plus the one thing only an
    exogena detail carries: the trailing `(Concepto: 2276)` code, which varies
    between rows that say the same thing.
    """
    return fold(CONCEPT_CODE.sub(" ", text or ""))


def concept_id_for(detail: str) -> str:
    """The concept a detail wording denotes, curated or not."""
    normalized = normalize(detail)
    if not normalized:
        return f"{UNCURATED_PREFIX}unknown"
    for wording, concept_id, _ in sorted(_SPINE_CONCEPTS, key=lambda c: -len(c[0])):
        if normalized.startswith(wording):
            return concept_id
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")[:60]
    return f"{UNCURATED_PREFIX}{slug or 'unknown'}"


def concept_code_in(detail: str) -> str:
    match = CONCEPT_CODE.search(detail or "")
    return match.group(1) if match else ""


def build_catalog() -> ConceptCatalog:
    return ConceptCatalog(
        [
            *(
                Concept(id=concept_id, label=label, role=FactRole.SPINE)
                for _, concept_id, label in _SPINE_CONCEPTS
            ),
            *(
                Concept(id=concept_id, label=label, role=FactRole.EVIDENCE)
                for concept_id, label in _EVIDENCE_CONCEPTS
            ),
        ]
    )
