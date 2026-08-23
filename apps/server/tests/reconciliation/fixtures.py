"""Fixtures drawn from a real 2025 exogena report and the two bank certificates
that back part of it.

The figures are verbatim, because they are what proves the arithmetic; the
taxpayer's identity is not, and has been replaced. The reporting parties keep
their real NITs since the rule pack keys on them and they identify companies,
not people.
"""

from __future__ import annotations

import io

from openpyxl import Workbook

from server.reconciliation.core.projection import ConceptMapping, ConceptMappingEntry

TAXPAYER_TAX_ID = "79999999"
TAXPAYER_NAME = "CONTRIBUYENTE DE PRUEBA"

BANCOLOMBIA = "890903938"
FIDUCIARIA = "800150280"
DAVIBANK = "860034594"
NU = "901658107"
ALIANZA = "860531315"
CARDIF = "900200435"
PROTECCION = "800170494"
EMPLOYER = "900809691"

# (reporter nit, reporter name, detail, value, additional info)
EXOGENA_ROWS: tuple[tuple[str, str, str, int, str], ...] = (
    (EMPLOYER, "LA HAUS S.A.S.", "Pagos por salarios (Concepto: 2276)", 129604000, ""),
    (
        FIDUCIARIA,
        "FIDUCIARIA BANCOLOMBIA S A SOCIEDAD FIDUCIARIA",
        "Retención practicada rendimientos  o utilidades en el periodo (Concepto: 1301)",
        19586,
        "",
    ),
    (
        FIDUCIARIA,
        "FIDUCIARIA BANCOLOMBIA S A SOCIEDAD FIDUCIARIA",
        "Cartera Colectiva Rendimientos Pagados (Titular Principal) (Concepto: 5063)",
        347071,
        "",
    ),
    (
        FIDUCIARIA,
        "FIDUCIARIA BANCOLOMBIA S A SOCIEDAD FIDUCIARIA",
        "Saldo Inversión en fondos de inversión colectiva (Titular Principal)",
        9102340,
        "Número de Cuenta / Documento: 0006302947 | Concepto Códigos Transaccionales: *1*",
    ),
    (
        FIDUCIARIA,
        "FIDUCIARIA BANCOLOMBIA S A SOCIEDAD FIDUCIARIA",
        "Inversiones en fondos de inversión colectiva realizadas durante el año",
        70600000,
        "Número de Cuenta / Documento: 0006302947",
    ),
    (
        BANCOLOMBIA,
        "BANCOLOMBIA S.A.",
        "Cuentas por pagar de clientes (Concepto: 1315)",
        146231584,
        "",
    ),
    (
        BANCOLOMBIA,
        "BANCOLOMBIA S.A.",
        "Saldo cuentas bancarias (Titular Principal)",
        2135378,
        "Número de Cuenta / Documento: 87041292758",
    ),
    (
        BANCOLOMBIA,
        "BANCOLOMBIA S.A.",
        "Saldo cuentas bancarias (Titular Principal)",
        105897,
        "Número de Cuenta / Documento: 64729058562",
    ),
    (
        BANCOLOMBIA,
        "BANCOLOMBIA S.A.",
        "Total consumos o gastos con tarjeta Crédito o Débito (Concepto: 5064)",
        36508272,
        "Número de Cuenta / Documento: 9383 | Clase de Tarjeta: *1*Ticket",
    ),
    (
        BANCOLOMBIA,
        "BANCOLOMBIA S.A.",
        "Aporte cuentas de ahorro para el fomento de la construcción (Concepto: 1022)",
        20800000,
        "Tipo de Aporte: *3* AFC",
    ),
    (
        DAVIBANK,
        "BANCO DAVIBANK S.A.",
        "Total consumos o gastos con tarjeta Crédito o Débito (Concepto: 5064)",
        1598066,
        "Número de Cuenta / Documento: 14001000012176710",
    ),
    (
        NU,
        "NU COLOMBIA COMPAÑIA DE FINANCIAMIENTO S.A.",
        "Intereses y rendimientos financieros pagados (Concepto: 5063)",
        399298,
        "Número de Cuenta / Documento: 47393555",
    ),
    (
        ALIANZA,
        "ALIANZA FIDUCIARIA S.A.",
        "Inversiones en fondos de inversión colectiva realizadas durante el año",
        8400000,
        "Número de Cuenta / Documento: 10041295055",
    ),
    (
        CARDIF,
        "CARDIF COLOMBIA SEGUROS GENERALES S.A.",
        "Cuentas por pagar de clientes (Concepto: 1315)",
        446629,
        "",
    ),
    (
        PROTECCION,
        "FONDO DE CESANTIA PROTECCION",
        "Valor total de las cesantías abonadas en el periodo.  (Formato 2276)",
        10499895,
        "Tipo de Afiliado: *1* Trabajador",
    ),
)


def exogena_workbook_bytes(year: int = 2025) -> bytes:
    """Rebuild the DIAN's layout: a preamble, then the reported rows.

    The preamble matters to the parser — the tax year and the taxpayer are read
    from it — so the fixture reproduces it rather than starting at the header.
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Reporte"
    sheet.append(["", "Consulta de Información reportada por terceros"])
    sheet.append(["ADVERTENCIA: Esta información es de caracter informativo"])
    sheet.append(["Fecha corte del proceso: ", "", f"{year + 1}-08-22 00:00:00"])
    sheet.append(["Año al que se refiere la consulta:", "", year])
    sheet.append(["Identificación del consultante"])
    sheet.append(["Tipo de documento:", "", "C. C."])
    sheet.append(["Identificación:", "", TAXPAYER_TAX_ID])
    sheet.append(["Nombres / Razón social:", "", TAXPAYER_NAME])
    sheet.append([])
    sheet.append(["Persona que reporta", "", "Información reportada"])
    sheet.append(
        [
            "NIT",
            "Nombre / Razón Social",
            "NIT",
            "Nombre/Razón Social reportada por el tercero",
            "Detalle",
            "Valor",
            "Uso declaración Sugerida",
            "Información  Adicional ",
        ]
    )
    # The DIAN's own aggregates sit between the header and the reported rows,
    # with no reporting party. The parser must skip them.
    for label, value in (("Tope 1 - Ingresos", 215231376), ("Tope 2 - Patrimonio", 490704000)):
        sheet.append([None, None, None, None, label, value, None, None])
    for reporter_nit, reporter_name, detail, value, extra in EXOGENA_ROWS:
        sheet.append(
            [
                reporter_nit,
                reporter_name,
                TAXPAYER_TAX_ID,
                TAXPAYER_NAME,
                detail,
                value,
                "",
                extra,
            ]
        )
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


# --- The two certificates, as OCR plus a concept mapping would deliver them ---

FIDUCIARIA_CERTIFICATE_FIELDS = {
    "agente_retenedor_nit": "800150280-0",
    "agente_retenedor_nombre": "FIDUCIARIA BANCOLOMBIA S.A.",
    "ano_gravable": "2025",
    "rendimientos_causados_total": "337,587.81",
    "rendimientos_pagados_total": "347,071.28",
    "base_gravable_total": "584,682.78",
    "retencion_total": "19,586.35",
    "cuentas": [
        {
            "numero": "0006000302947",
            "saldo_dic_31": "9,102,339.53",
        }
    ],
}

BANCOLOMBIA_CERTIFICATE_FIELDS = {
    "agente_retenedor_nit": "890903938-8",
    "agente_retenedor_nombre": "Bancolombia S.A.",
    "ano_gravable": "2025",
    "saldo_cuenta_ahorros": "$ 2,241,275.17",
    "cartera_capital": "$ 143,944,539.00",
    "cartera_interes": "$ 564,262.00",
    "cartera_otros": "$ 446,629.00",
    "tarjeta_credito_capital": "$ 1,276,145.50",
    "intereses_causados_cartera": "$ 9,946,131.00",
    "gmf_base": "$ 128,140,380.00",
    "gmf_valor": "$ 512,561.52",
}

FIDUCIARIA_MAPPING = ConceptMapping(
    document_type_id="type-fiduciaria-cert",
    kind_id="exogena_dian",
    reporter_path="agente_retenedor_nit",
    reporter_name_path="agente_retenedor_nombre",
    entries=(
        ConceptMappingEntry("retencion_total", "bank:cert_retencion_total"),
        ConceptMappingEntry("rendimientos_pagados_total", "bank:cert_rendimientos_pagados"),
        ConceptMappingEntry("rendimientos_causados_total", "bank:cert_rendimientos_causados"),
        ConceptMappingEntry("base_gravable_total", "bank:cert_base_gravable_retencion"),
        ConceptMappingEntry(
            "cuentas[].saldo_dic_31",
            "bank:cert_saldo_inversion",
            account_path="cuentas[].numero",
        ),
    ),
)

BANCOLOMBIA_MAPPING = ConceptMapping(
    document_type_id="type-bancolombia-cert",
    kind_id="exogena_dian",
    reporter_path="agente_retenedor_nit",
    reporter_name_path="agente_retenedor_nombre",
    entries=(
        ConceptMappingEntry("saldo_cuenta_ahorros", "bank:cert_saldo_cuentas_ahorro"),
        ConceptMappingEntry("cartera_capital", "bank:cert_cartera_capital"),
        ConceptMappingEntry("cartera_interes", "bank:cert_cartera_interes"),
        ConceptMappingEntry("cartera_otros", "bank:cert_cartera_otros"),
        ConceptMappingEntry("tarjeta_credito_capital", "bank:cert_tarjeta_credito_capital"),
        ConceptMappingEntry("intereses_causados_cartera", "bank:cert_intereses_causados"),
        ConceptMappingEntry("gmf_base", "bank:cert_gmf_base"),
        ConceptMappingEntry("gmf_valor", "bank:cert_gmf_valor"),
    ),
)
