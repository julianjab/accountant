"""The kernel's value objects, whose edge cases decide whether two sources are
talking about the same thing."""

from __future__ import annotations

from decimal import Decimal

import pytest

from server.shared import Money, Period, PeriodGranularity, TaxId
from server.shared.money import parse_amount


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("$ 2,241,275.17", "2241275.17"),
        ("143.944.539,00", "143944539.00"),
        ("9,102,339.53", "9102339.53"),
        ("4.418.000", "4418000.00"),
        ("512561.52", "512561.52"),
        ("(1.234)", "-1234.00"),
        ("-19,586.35", "-19586.35"),
        (146231584, "146231584.00"),
        (Decimal("0.01"), "0.01"),
    ],
)
def test_amounts_are_read_from_every_format_the_sources_use(raw, expected):
    assert Money.parse(raw) == Money.of(expected)


@pytest.mark.parametrize("raw", [None, "", "   ", "no digits", True, False])
def test_a_field_with_no_number_is_absent_not_zero(raw):
    """Emitting zero here would turn "the bank never said" into "the bank said
    nil", which reconciles against nothing and hides the gap."""
    assert Money.parse(raw) is None
    assert parse_amount(raw) is None


def test_money_arithmetic_stays_exact():
    total = Money.of("2135378") + Money.of("105897")
    assert total == Money.of("2241275")
    assert (total - Money.of("2241275.17")) == Money.of("-0.17")
    assert (-Money.of("5")).amount == Decimal("-5.00")
    assert (Money.of("5") * -1) == Money.of("-5")
    assert Money.of("-3").abs() == Money.of("3")
    assert Money.zero().is_zero
    assert str(Money.of("1234567.5")) == "1,234,567.50"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("890903938-8", "890903938"),
        ("890.903.938", "890903938"),
        (" 1038409218 ", "1038409218"),
        (1038409218, "1038409218"),
    ],
)
def test_tax_ids_normalize_to_the_identifier_without_its_check_digit(raw, expected):
    assert TaxId.parse(raw) == TaxId(expected)


@pytest.mark.parametrize("raw", [None, "", "   ", "N/A"])
def test_an_absent_tax_id_parses_to_nothing(raw):
    assert TaxId.parse(raw) is None


def test_periods_print_and_compare_by_their_key():
    assert Period.of_year(2025).key == "2025"
    assert Period.of_month(2025, 3).key == "2025-03"
    assert str(Period.of_year(2025)) == "2025"
    assert Period.of_year(2024) < Period.of_year(2025)
    assert Period.of_year(2025) != Period.of_month(2025, 3)


@pytest.mark.parametrize(
    ("granularity", "year", "month", "message"),
    [
        (PeriodGranularity.MONTH, 2025, None, "requires a month"),
        (PeriodGranularity.YEAR, 2025, 3, "must not carry a month"),
        (PeriodGranularity.MONTH, 2025, 13, "out of range"),
        (PeriodGranularity.MONTH, 2025, 0, "out of range"),
    ],
)
def test_an_incoherent_period_is_rejected_on_construction(granularity, year, month, message):
    with pytest.raises(ValueError, match=message):
        Period(granularity, year, month)
