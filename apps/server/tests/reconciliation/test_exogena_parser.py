"""The exogena parser, including the failure modes that would otherwise return
a clean-looking but wrong report."""

from __future__ import annotations

import io
import zipfile

import fixtures
import pytest
from openpyxl import Workbook

from server.reconciliation.core.kind import SourceContent, SourceNotRecognized
from server.reconciliation.kinds.exogena.xlsx_parser import (
    ExogenaParseError,
    ExogenaXlsxExtractor,
)
from server.shared import FactRole, Money, Period

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _extract(data: bytes, **kw):
    return ExogenaXlsxExtractor().extract(
        SourceContent(data=data, media_type=XLSX, file_name="e.xlsx", source_id="doc-1", **kw)
    )


def _workbook(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    for row in rows:
        workbook.active.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_every_reported_row_becomes_a_spine_fact():
    facts = _extract(fixtures.exogena_workbook_bytes())
    assert len(facts) == len(fixtures.EXOGENA_ROWS)
    assert all(f.role is FactRole.SPINE for f in facts)
    assert all(f.source_id == "doc-1" for f in facts)


def test_the_tax_year_is_read_from_the_report_not_assumed():
    """The preamble also carries the run date; picking that one would file the
    whole report under the wrong year."""
    facts = _extract(fixtures.exogena_workbook_bytes(year=2023))
    assert {f.period for f in facts} == {Period.of_year(2023)}


def test_an_explicit_period_overrides_the_one_in_the_file():
    facts = _extract(fixtures.exogena_workbook_bytes(), period=Period.of_year(2019))
    assert {f.period for f in facts} == {Period.of_year(2019)}


def test_the_dian_own_aggregates_are_skipped():
    """The `Tope N` rows have no reporting party: they are the DIAN's own sums
    over the rows below, not third-party claims to reconcile."""
    facts = _extract(fixtures.exogena_workbook_bytes())
    assert all("Tope" not in f.detail for f in facts)
    assert Money.of(215231376) not in {f.amount for f in facts}


def test_account_numbers_and_extras_are_pulled_out_of_the_free_text_column():
    facts = _extract(fixtures.exogena_workbook_bytes())
    by_account = {f.account.digits: f for f in facts if f.account}
    assert "0006302947" in by_account
    # A card reaches us as a four-digit mask and nothing more.
    assert "9383" in by_account
    card = by_account["9383"]
    assert card.extras["clase_de_tarjeta"] == "*1*Ticket"
    assert card.extras["dian_concept_code"] == "5064"


def test_rows_carry_a_locator_back_to_the_spreadsheet():
    facts = _extract(fixtures.exogena_workbook_bytes())
    assert all(f.locator.startswith("row ") for f in facts)
    assert len({f.locator for f in facts}) == len(facts)


def test_the_subject_is_read_from_the_preamble():
    facts = _extract(fixtures.exogena_workbook_bytes())
    assert all(f.subject_tax_id.value == fixtures.TAXPAYER_TAX_ID for f in facts)


def test_a_spreadsheet_that_is_not_an_exogena_is_reported_as_unrecognized():
    """An ordinary outcome — a client's folder holds all sorts of files — and
    distinct from a malformed report, which must surface."""
    with pytest.raises(SourceNotRecognized):
        _extract(_workbook([["Fecha", "Concepto", "Débito"], ["2025-01-01", "x", 10]]))


def test_a_report_with_a_header_but_no_rows_is_an_error_not_an_empty_result():
    """Silence here would read as "nothing to reconcile" for a client whose
    report simply failed to parse."""
    data = _workbook(
        [
            ["Año al que se refiere la consulta:", "", 2025],
            ["NIT", "Nombre", "NIT", "Nombre", "Detalle", "Valor", "Uso", "Info"],
        ]
    )
    with pytest.raises(ExogenaParseError, match="no reported rows"):
        _extract(data)


def test_a_report_with_no_stated_year_is_an_error():
    data = _workbook(
        [
            ["Identificación:", "", "79999999"],
            ["NIT", "Nombre", "NIT", "Nombre", "Detalle", "Valor", "Uso", "Info"],
            [
                "890903938",
                "BANCOLOMBIA S.A.",
                "79999999",
                "X",
                "Saldo cuentas bancarias",
                10,
                "",
                "",
            ],
        ]
    )
    with pytest.raises(ExogenaParseError, match="tax year"):
        _extract(data)


def test_rows_missing_a_detail_or_an_amount_are_skipped():
    data = _workbook(
        [
            ["Año al que se refiere la consulta:", "", 2025],
            ["NIT", "Nombre", "NIT", "Nombre", "Detalle", "Valor", "Uso", "Info"],
            ["890903938", "BANCOLOMBIA S.A.", "79999999", "X", "", 10, "", ""],
            [
                "890903938",
                "BANCOLOMBIA S.A.",
                "79999999",
                "X",
                "Saldo cuentas bancarias",
                "",
                "",
                "",
            ],
            [
                "890903938",
                "BANCOLOMBIA S.A.",
                "79999999",
                "X",
                "Saldo cuentas bancarias",
                10,
                "",
                "",
            ],
        ]
    )
    facts = _extract(data)
    assert len(facts) == 1
    assert facts[0].amount == Money.of(10)


def test_a_row_shorter_than_the_header_does_not_crash_the_parse():
    data = _workbook(
        [
            ["Año al que se refiere la consulta:", "", 2025],
            ["NIT", "Nombre", "NIT", "Nombre", "Detalle", "Valor", "Uso", "Info"],
            ["890903938", "BANCOLOMBIA S.A.", "79999999", "X", "Saldo cuentas bancarias", 10],
        ]
    )
    facts = _extract(data)
    assert len(facts) == 1
    assert facts[0].account is None


def _with_decimal_numbers(data: bytes, values: tuple[int, ...]) -> bytes:
    """The same workbook with those numeric cells written as `N.0`.

    openpyxl always writes a whole number without a decimal point, so a
    workbook built here cannot reproduce what the DIAN's file actually holds.
    """
    source = zipfile.ZipFile(io.BytesIO(data))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as target:
        for item in source.infolist():
            content = source.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                for value in values:
                    content = content.replace(
                        f"<v>{value}</v>".encode(), f"<v>{value}.0</v>".encode()
                    )
            target.writestr(item, content)
    return buffer.getvalue()


def test_a_nit_written_as_a_decimal_does_not_grow_a_digit():
    """A NIT cell holding `890903938.0` comes back from openpyxl as a float.

    Stringifying it kept the decimal point, so the party reached the engine as
    `8909039380` and no exogena row could pair with the certificate naming the
    same party — every row of a real report read as "certificate not found".
    """
    data = _workbook(
        [
            ["Año al que se refiere la consulta:", "", 2025],
            ["NIT", "Nombre", "NIT", "Nombre", "Detalle", "Valor", "Uso", "Info"],
            [
                890903938,
                "BANCOLOMBIA S.A.",
                1038409218,
                "X",
                "Cuentas por pagar de clientes (Concepto: 1315)",
                146231584,
                "",
                "",
            ],
        ]
    )
    (fact,) = _extract(_with_decimal_numbers(data, (890903938, 1038409218)))
    assert str(fact.reporter_tax_id) == "890903938"
    assert str(fact.subject_tax_id) == "1038409218"
