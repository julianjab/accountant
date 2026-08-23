"""The DIAN exogena's vocabulary, and the bank-certificate vocabulary it is
checked against.

Everything model-specific lives here. `reconciliation.core` never imports this
module; it only ever sees opaque concept ids.
"""

from __future__ import annotations

import re
import unicodedata

from server.reconciliation.core.concepts import Concept, ConceptCatalog
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
)

UNCURATED_PREFIX = "dian:x-"


def normalize(text: str) -> str:
    """Fold a detail wording down to something matchable.

    The same concept reaches us with different accents, casing, double spaces
    and a trailing concept code, so all four are removed before comparison.
    """
    without_code = CONCEPT_CODE.sub(" ", text or "")
    decomposed = unicodedata.normalize("NFKD", without_code)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", stripped).strip().lower()


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
