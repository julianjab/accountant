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


class TestValuesTheDocumentNeverStates:
    """A certificate that never prints its own issuer.

    Plenty of them identify the taxpayer and never themselves: the letterhead
    says who they are and the text does not repeat it. The figures are still
    that issuer's, but with nothing on the page saying so every fact was
    discarded and every claim the certificate backed came back as missing
    evidence — a real certificate reported as absent.
    """

    def test_a_type_can_declare_who_reports_when_the_paper_does_not(self):
        facts = _project(
            _mapping(
                [ConceptMappingEntry("saldo", "ev:saldo")],
                reporter_tax_id="890.903.938-8",
            ),
            {"saldo": "1000"},
        )

        assert facts[0].reporter_tax_id == TaxId("890903938")

    def test_what_the_document_says_beats_what_the_type_declares(self):
        """Configuration fills a silence; it must never overrule a paper that
        does state its issuer, or figures get attributed to the wrong party."""
        facts = _project(
            _mapping(
                [ConceptMappingEntry("saldo", "ev:saldo")],
                reporter_path="nit",
                reporter_tax_id="800170494",
            ),
            {"nit": "890903938-8", "saldo": "1000"},
        )

        assert facts[0].reporter_tax_id == TaxId("890903938")

    def test_the_declared_party_covers_a_document_whose_field_came_back_empty(self):
        """The field exists and the OCR read nothing into it — which is the
        same silence, and the reason to declare the party in the first place."""
        facts = _project(
            _mapping(
                [ConceptMappingEntry("saldo", "ev:saldo")],
                reporter_path="nit",
                reporter_tax_id="800170494",
            ),
            {"nit": "", "saldo": "1000"},
        )

        assert facts[0].reporter_tax_id == TaxId("800170494")

    def test_a_declared_name_is_used_when_the_paper_does_not_name_the_issuer(self):
        facts = _project(
            _mapping(
                [ConceptMappingEntry("saldo", "ev:saldo")],
                reporter_tax_id="890903938",
                reporter_name="JFK Cooperativa Financiera",
            ),
            {"saldo": "1000"},
        )

        assert facts[0].reporter_name == "JFK Cooperativa Financiera"

    def test_a_declared_period_places_a_certificate_that_states_no_year(self):
        facts = _project(
            _mapping(
                [ConceptMappingEntry("saldo", "ev:saldo")],
                reporter_tax_id="890903938",
                period="2024",
            ),
            {"saldo": "1000"},
        )

        assert facts[0].period == Period.of_year(2024)

    def test_the_year_on_the_paper_beats_the_declared_one(self):
        facts = _project(
            _mapping(
                [ConceptMappingEntry("saldo", "ev:saldo")],
                reporter_tax_id="890903938",
                period_path="anio",
                period="2024",
            ),
            {"anio": "2025", "saldo": "1000"},
        )

        assert facts[0].period == Period.of_year(2025)

    def test_a_declared_party_that_is_not_a_number_is_refused_at_configuration(self):
        """Left to projection it resolves to nothing, the mapping falls back to
        the caller's party, and the type reads as configured while attributing
        its figures to somebody else."""
        with pytest.raises(ValueError, match="not a tax id"):
            _mapping([], reporter_tax_id="JFK Cooperativa Financiera")

    def test_a_declared_period_with_no_year_in_it_is_refused(self):
        with pytest.raises(ValueError, match="does not contain a year"):
            _mapping([], reporter_tax_id="890903938", period="vigencia actual")


# --- A document that prints a table, not labelled boxes ---------------------
#
# An employment certificate (DIAN form 220) states sixteen income lines in one
# repeated block: each row says what it is and how much. One path claiming
# every row is the wrong reading of that block, and these pin the right one.

_CERT_220 = {
    "nit": "890903938",
    "ingresos": [
        {"concepto": "Pagos por salarios", "valor": "80.000.000"},
        {"concepto": "Pagos por prestaciones sociales", "valor": "7.000.000"},
        {"concepto": "Auxilio de cesantía consignado al fondo de cesantías", "valor": "6.500.000"},
        {"concepto": "Pagos por viáticos", "valor": "1.200.000"},
    ],
}


def _row_entry(label, concept):
    return ConceptMappingEntry(
        "ingresos[].valor",
        concept,
        row_label_path="ingresos[].concepto",
        row_label=label,
    )


def test_each_row_of_a_table_projects_under_its_own_concept():
    facts = _project(
        _mapping(
            [
                _row_entry("Pagos por salarios", "payroll:salarios"),
                _row_entry(
                    "Auxilio de cesantía consignado al fondo de cesantías",
                    "payroll:cesantias_consignadas",
                ),
            ],
            reporter_path="nit",
        ),
        _CERT_220,
    )
    assert {(f.concept_id, f.amount) for f in facts} == {
        ("payroll:salarios", Money.of("80000000")),
        ("payroll:cesantias_consignadas", Money.of("6500000")),
    }


def test_a_row_nobody_mapped_contributes_nothing():
    """Viáticos are stated on the paper and mapped to no concept, so they must
    not be swept into the concept of the row above them."""
    facts = _project(
        _mapping([_row_entry("Pagos por salarios", "payroll:salarios")], reporter_path="nit"),
        _CERT_220,
    )
    assert [f.amount for f in facts] == [Money.of("80000000")]


def test_a_row_wording_is_matched_past_accents_casing_and_spacing():
    """The same box, printed by two payroll systems."""
    facts = _project(
        _mapping(
            [_row_entry("Auxilio de cesantía consignado al fondo de cesantías", "payroll:cons")],
            reporter_path="nit",
        ),
        {
            "nit": "890903938",
            "ingresos": [
                {"concepto": "AUXILIO DE  CESANTIA CONSIGNADO AL FONDO DE CESANTIAS ", "valor": "9"}
            ],
        },
    )
    assert [f.concept_id for f in facts] == ["payroll:cons"]


def test_a_row_that_does_not_say_what_it_is_belongs_to_nobody():
    """Better an unexplained figure than one filed under a concept on no
    evidence: a wrong DIAN line reconciles quietly and reads as correct."""
    facts = _project(
        _mapping([_row_entry("Pagos por salarios", "payroll:salarios")], reporter_path="nit"),
        {"nit": "890903938", "ingresos": [{"valor": "80.000.000"}]},
    )
    assert facts == ()


def test_an_undiscriminated_entry_still_claims_every_element():
    """The repeated block whose elements are all the same thing — one balance
    per account — must keep working exactly as it did."""
    facts = _project(
        _mapping([ConceptMappingEntry("ingresos[].valor", "ev:todo")], reporter_path="nit"),
        _CERT_220,
    )
    assert len(facts) == 4


def test_a_row_wording_without_the_field_stating_it_is_refused():
    with pytest.raises(ValueError, match="only mean something together"):
        ConceptMappingEntry("ingresos[].valor", "ev:x", row_label="Pagos por salarios")


def test_a_field_stating_the_row_without_a_wording_is_refused():
    with pytest.raises(ValueError, match="only mean something together"):
        ConceptMappingEntry("ingresos[].valor", "ev:x", row_label_path="ingresos[].concepto")


def test_a_blank_row_wording_is_refused():
    with pytest.raises(ValueError, match="cannot be blank"):
        ConceptMappingEntry(
            "ingresos[].valor", "ev:x", row_label_path="ingresos[].concepto", row_label="  "
        )
