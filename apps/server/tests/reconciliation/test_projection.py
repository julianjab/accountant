"""Projecting OCR output onto the shared vocabulary — the seam where the two
halves of the product meet."""

from __future__ import annotations

import pytest

from server.reconciliation.core.projection import (
    ConceptMapping,
    ConceptMappingEntry,
    project_facts,
)
from server.shared import Money, Period, TaxId

YEAR = Period.of_year(2025)


def _mapping(entries, **kw):
    return ConceptMapping(document_type_id="t", kind_id="k", entries=tuple(entries), **kw)


def _project(mapping, fields, **kw):
    return project_facts(mapping, fields, source_id="doc-1", period=YEAR, **kw)


def test_a_flat_field_becomes_one_fact():
    facts = _project(
        _mapping([ConceptMappingEntry("saldo", "ev:saldo")], reporter_path="nit"),
        {"nit": "890903938-8", "saldo": "$ 1.000,50"},
    )
    assert len(facts) == 1
    assert facts[0].amount == Money.of("1000.50")
    assert facts[0].reporter_tax_id == TaxId("890903938")
    assert facts[0].source_id == "doc-1"


def test_a_repeated_block_becomes_one_fact_per_entry_with_its_own_account():
    """A certificate that discloses several accounts must not collapse them."""
    facts = _project(
        _mapping(
            [ConceptMappingEntry("cuentas[].saldo", "ev:saldo", account_path="cuentas[].numero")],
            reporter_path="nit",
        ),
        {
            "nit": "890903938",
            "cuentas": [
                {"numero": "64729058562", "saldo": "100"},
                {"numero": "87041292758", "saldo": "200"},
            ],
        },
    )
    assert [f.account.digits for f in facts] == ["64729058562", "87041292758"]
    assert [f.amount for f in facts] == [Money.of(100), Money.of(200)]


def test_a_negative_entry_subtracts():
    facts = _project(
        _mapping([ConceptMappingEntry("cargo", "ev:x", sign=-1)], reporter_path="nit"),
        {"nit": "890903938", "cargo": "50"},
    )
    assert facts[0].amount == Money.of(-50)


def test_fields_the_document_never_stated_produce_no_facts():
    facts = _project(
        _mapping(
            [
                ConceptMappingEntry("ausente", "ev:a"),
                ConceptMappingEntry("vacio", "ev:b"),
                ConceptMappingEntry("texto", "ev:c"),
            ],
            reporter_path="nit",
        ),
        {"nit": "890903938", "vacio": "", "texto": "no aplica"},
    )
    assert facts == ()


def test_the_period_the_document_states_wins_over_the_one_requested():
    """Otherwise a 2024 certificate uploaded into a 2025 reconciliation would
    quietly reconcile against the wrong year."""
    facts = _project(
        _mapping(
            [ConceptMappingEntry("saldo", "ev:saldo")],
            reporter_path="nit",
            period_path="ano_gravable",
        ),
        {"nit": "890903938", "ano_gravable": "Año gravable 2024", "saldo": "10"},
    )
    assert facts[0].period == Period.of_year(2024)


@pytest.mark.parametrize("fields", [{"nit": "890903938"}, {"nit": "890903938", "ano": "n/a"}])
def test_an_unreadable_stated_period_falls_back_to_the_requested_one(fields):
    facts = _project(
        _mapping(
            [ConceptMappingEntry("saldo", "ev:saldo")],
            reporter_path="nit",
            period_path="ano",
        ),
        {**fields, "saldo": "10"},
    )
    assert facts[0].period == YEAR


def test_a_monthly_reconciliation_does_not_infer_its_period_from_a_year_field():
    facts = project_facts(
        _mapping(
            [ConceptMappingEntry("saldo", "ev:saldo")],
            reporter_path="nit",
            period_path="ano",
        ),
        {"nit": "890903938", "ano": "2024", "saldo": "10"},
        source_id="doc-1",
        period=Period.of_month(2025, 3),
    )
    assert facts[0].period == Period.of_month(2025, 3)


def test_the_reporting_party_falls_back_to_the_caller_when_the_document_omits_it():
    facts = _project(
        _mapping([ConceptMappingEntry("saldo", "ev:saldo")], reporter_path="nit"),
        {"saldo": "10"},
        reporter_tax_id=TaxId("860034594"),
        reporter_name="Davibank",
    )
    assert facts[0].reporter_tax_id == TaxId("860034594")
    assert facts[0].reporter_name == "Davibank"


def test_amounts_that_cannot_be_attributed_to_anyone_are_refused():
    """Attributing them to a guess would reconcile the wrong party's claim."""
    with pytest.raises(ValueError, match="no reporting party"):
        _project(
            _mapping([ConceptMappingEntry("saldo", "ev:saldo")], reporter_path="nit"),
            {"saldo": "10"},
        )


@pytest.mark.parametrize(
    "path",
    [
        "no.existe",
        "cuentas[].falta",
        "saldo.mas.hondo",
        "cuentas[9].saldo",
        "escalar[].saldo",
    ],
)
def test_a_path_that_does_not_resolve_yields_nothing_rather_than_failing(path):
    facts = _project(
        _mapping([ConceptMappingEntry(path, "ev:x")], reporter_path="nit"),
        {"nit": "890903938", "saldo": "10", "escalar": "texto", "cuentas": [{"saldo": "1"}]},
    )
    assert facts == ()


def test_an_account_path_that_does_not_resolve_leaves_the_fact_unidentified():
    facts = _project(
        _mapping(
            [ConceptMappingEntry("saldo", "ev:x", account_path="cuenta.numero")],
            reporter_path="nit",
        ),
        {"nit": "890903938", "saldo": "10"},
    )
    assert facts[0].account is None


def test_the_reporter_name_is_read_from_the_document_when_mapped():
    facts = _project(
        _mapping(
            [ConceptMappingEntry("saldo", "ev:x")],
            reporter_path="nit",
            reporter_name_path="nombre",
        ),
        {"nit": "890903938", "nombre": " Bancolombia S.A. ", "saldo": "10"},
    )
    assert facts[0].reporter_name == "Bancolombia S.A."


@pytest.mark.parametrize(
    "account_path",
    [
        "cuentas[abc].numero",  # not a resolvable subscript
        "cuentas[5].numero",  # past the end of the list
        "nit[0]",  # subscripting something that is not a list
    ],
)
def test_a_malformed_or_out_of_range_account_path_leaves_the_fact_unidentified(account_path):
    """A hand-written mapping must degrade to "no account", never crash the
    whole reconciliation."""
    facts = _project(
        _mapping(
            [ConceptMappingEntry("saldo", "ev:x", account_path=account_path)],
            reporter_path="nit",
        ),
        {"nit": "890903938", "saldo": "10", "cuentas": [{"numero": "1"}]},
    )
    assert len(facts) == 1
    assert facts[0].account is None


def test_an_entry_with_no_account_path_is_left_unidentified():
    facts = _project(
        _mapping([ConceptMappingEntry("saldo", "ev:x")], reporter_path="nit"),
        {"nit": "890903938", "saldo": "10"},
    )
    assert facts[0].account is None


@pytest.mark.parametrize("sign", [0, 2, -2])
def test_a_mapping_entry_refuses_a_sign_that_is_neither_plus_nor_minus_one(sign):
    """0 would zero the field's amounts and 2 would double them, with nothing
    downstream to notice. These values arrive from an AI proposal and from an
    HTTP payload, so the entity itself refuses them."""
    with pytest.raises(ValueError, match="must be \\+1 or -1"):
        ConceptMappingEntry("saldo", "ev:x", sign=sign)


def test_comparing_per_account_requires_a_field_holding_the_account():
    """Otherwise the entry asks for a pairing that cannot happen, and a figure
    the certificate does state comes back reported as missing."""
    with pytest.raises(ValueError, match="requires an account_path"):
        ConceptMappingEntry("saldo", "ev:x", per_account=True)

    # With one, the same entry is fine.
    entry = ConceptMappingEntry("saldo", "ev:x", account_path="cuenta", per_account=True)
    assert entry.per_account
