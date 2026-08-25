"""Keeping a concept mapping honest when its extraction schema is edited.

A mapping entry names a path in the schema. Trim that field away and the entry
survives pointing at nothing: the projection finds no value, emits no fact, and
says nothing. The type still reads as configured while the claim it was meant
to satisfy is reported as missing evidence — the failure with the longest trail
back to its cause in this product, which is why the edit resolves it eagerly.
"""

from __future__ import annotations

from server.reconciliation.application import (
    MappingChangeKind,
    PruneConceptMappings,
    PruneConceptMappingsInput,
)
from server.reconciliation.core.projection import ConceptMapping, ConceptMappingEntry
from server.reconciliation.core.registry import KindRegistry
from server.reconciliation.infrastructure import InMemoryConceptMappingRepository
from server.reconciliation.kinds.exogena import KIND_ID, ExogenaReconciliation

SALDO = "bank:cert_saldo_cuentas_ahorro"
GMF = "bank:cert_gmf_valor"

FULL_SCHEMA = {
    "type": "object",
    "properties": {
        "nit": {"type": "string"},
        "razon_social": {"type": "string"},
        "anio": {"type": "string"},
        "gmf": {"type": "string"},
        "cuentas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "numero": {"type": "string"},
                    "saldo": {"type": "string"},
                },
            },
        },
    },
}


def _schema_without(*dropped: str) -> dict:
    """The same schema with some top-level or account properties removed."""
    schema = {
        "type": "object",
        "properties": {
            key: value for key, value in FULL_SCHEMA["properties"].items() if key not in dropped
        },
    }
    accounts = schema["properties"].get("cuentas")
    if accounts is not None:
        schema["properties"]["cuentas"] = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    key: value
                    for key, value in accounts["items"]["properties"].items()
                    if f"cuentas[].{key}" not in dropped
                },
            },
        }
    return schema


def _mapping(**overrides) -> ConceptMapping:
    defaults = dict(
        document_type_id="type-1",
        kind_id=KIND_ID,
        reporter_path="nit",
        reporter_name_path="razon_social",
        period_path="anio",
        entries=(
            ConceptMappingEntry("cuentas[].saldo", SALDO, account_path="cuentas[].numero"),
            ConceptMappingEntry("gmf", GMF),
        ),
    )
    defaults.update(overrides)
    return ConceptMapping(**defaults)


def _prune(schema, mapping=None):
    mappings = InMemoryConceptMappingRepository()
    mappings.save(mapping if mapping is not None else _mapping())
    changes = PruneConceptMappings(KindRegistry([ExogenaReconciliation()]), mappings).execute(
        PruneConceptMappingsInput(document_type_id="type-1", extraction_schema=schema)
    )
    return changes, mappings.get("type-1", KIND_ID)


def test_a_schema_that_still_declares_everything_leaves_the_mapping_alone():
    changes, mapping = _prune(FULL_SCHEMA)

    assert changes == ()
    assert mapping == _mapping()


def test_an_entry_whose_field_was_trimmed_away_is_dropped_and_reported():
    """Left in place it would produce no fact and no complaint, so the claim it
    backed would read as missing evidence with nothing naming the reason."""
    changes, mapping = _prune(_schema_without("gmf"))

    assert [e.field_path for e in mapping.entries] == ["cuentas[].saldo"]
    assert [(c.change, c.field_path, c.concept_id) for c in changes] == [
        (MappingChangeKind.ENTRY_DROPPED, "gmf", GMF)
    ]


def test_the_surviving_entries_keep_their_concept_sign_and_account():
    changes, mapping = _prune(_schema_without("gmf"))

    assert len(changes) == 1
    assert mapping.entries[0] == ConceptMappingEntry(
        "cuentas[].saldo", SALDO, account_path="cuentas[].numero"
    )


def test_an_amount_whose_account_field_vanished_keeps_reconciling():
    """Losing the account only weakens matching; dropping the amount too would
    throw away evidence the report can still use."""
    changes, mapping = _prune(_schema_without("cuentas[].numero"))

    assert mapping.entries[0].field_path == "cuentas[].saldo"
    assert mapping.entries[0].account_path is None
    assert [(c.change, c.path) for c in changes] == [
        (MappingChangeKind.PATH_CLEARED, "cuentas[].numero")
    ]


def test_a_mapping_that_lost_its_reporting_party_is_cleared_whole():
    """Every fact needs a party to attribute it to, so the projection discards
    this mapping entirely however many entries survive. Keeping them would show
    a mapped type whose extraction never reaches a report."""
    changes, mapping = _prune(_schema_without("nit"))

    assert mapping.entries == ()
    assert mapping.reporter_path is None
    assert [c.change for c in changes] == [MappingChangeKind.MAPPING_CLEARED]
    assert changes[0].path == "nit"


def test_a_period_field_that_vanished_is_cleared_rather_than_left_dangling():
    """The period path decides which year the document reconciles into; left
    pointing at nothing it silently falls back to the caller's year."""
    changes, mapping = _prune(_schema_without("anio"))

    assert mapping.period_path is None
    assert mapping.reporter_name_path == "razon_social"
    assert [(c.change, c.path) for c in changes] == [(MappingChangeKind.PATH_CLEARED, "anio")]


def test_a_document_type_with_no_mapping_is_simply_untouched():
    """Extraction-only types are ordinary — most edits have nothing to prune."""
    mappings = InMemoryConceptMappingRepository()

    changes = PruneConceptMappings(KindRegistry([ExogenaReconciliation()]), mappings).execute(
        PruneConceptMappingsInput(document_type_id="type-1", extraction_schema=FULL_SCHEMA)
    )

    assert changes == ()
    assert mappings.get("type-1", KIND_ID) is None


def test_a_schema_declaring_no_properties_prunes_nothing():
    """A schema that cannot be walked cannot disprove a path either, and
    dropping every mapping on a schema this code fails to understand would
    destroy configuration no one asked to change."""
    changes, mapping = _prune({"type": "object"})

    assert changes == ()
    assert mapping == _mapping()


def test_pruning_keeps_the_exogena_line_a_field_answers():
    """Pruning drops what a schema edit invalidated. Anything it does not own
    must survive, or every edit would quietly stop the field being compared."""
    mappings = InMemoryConceptMappingRepository()
    mappings.save(
        ConceptMapping(
            document_type_id="t1",
            kind_id=KIND_ID,
            reporter_path="nit",
            entries=(
                ConceptMappingEntry(
                    field_path="saldo",
                    concept_id="bank:cert_saldo_cuentas_ahorro",
                    spine_concept_id="dian:saldo-cuentas-bancarias",
                ),
            ),
        )
    )

    PruneConceptMappings(KindRegistry([ExogenaReconciliation()]), mappings).execute(
        PruneConceptMappingsInput(
            document_type_id="t1",
            extraction_schema={
                "type": "object",
                "properties": {"saldo": {"type": "string"}, "nit": {"type": "string"}},
            },
        )
    )

    kept = mappings.get("t1", KIND_ID)
    assert kept.entries[0].spine_concept_id == "dian:saldo-cuentas-bancarias"


def test_losing_the_account_field_downgrades_to_comparing_totals():
    """Rather than leaving a pairing that can never happen, which reads as a
    missing certificate for a figure the document does state."""
    mappings = InMemoryConceptMappingRepository()
    mappings.save(
        ConceptMapping(
            document_type_id="t1",
            kind_id=KIND_ID,
            reporter_path="nit",
            entries=(
                ConceptMappingEntry(
                    field_path="saldo",
                    concept_id="bank:cert_saldo_cuentas_ahorro",
                    spine_concept_id="dian:saldo-cuentas-bancarias",
                    account_path="cuenta",
                    per_account=True,
                ),
            ),
        )
    )

    PruneConceptMappings(KindRegistry([ExogenaReconciliation()]), mappings).execute(
        PruneConceptMappingsInput(
            document_type_id="t1",
            extraction_schema={
                "type": "object",
                "properties": {"saldo": {"type": "string"}, "nit": {"type": "string"}},
            },
        )
    )

    kept = mappings.get("t1", KIND_ID)
    assert kept.entries[0].account_path is None
    assert kept.entries[0].per_account is False
    assert kept.entries[0].spine_concept_id == "dian:saldo-cuentas-bancarias"


def test_a_type_that_declares_its_reporting_party_survives_losing_the_field():
    """The whole point of declaring it is that the document never says. Clearing
    the mapping because the schema stopped extracting a field it was not relying
    on would delete a working configuration."""
    mappings = InMemoryConceptMappingRepository()
    mappings.save(
        _mapping(
            reporter_path="nit",
            reporter_tax_id="890903938",
            entries=(ConceptMappingEntry("gmf", GMF),),
        )
    )

    changes = PruneConceptMappings(KindRegistry([ExogenaReconciliation()]), mappings).execute(
        PruneConceptMappingsInput(
            document_type_id="type-1", extraction_schema=_schema_without("nit")
        )
    )

    kept = mappings.get("type-1", KIND_ID)
    assert [e.field_path for e in kept.entries] == ["gmf"]
    assert kept.reporter_tax_id == "890903938"
    assert MappingChangeKind.MAPPING_CLEARED not in [c.change for c in changes]


def test_pruning_keeps_the_values_a_type_declares_for_itself():
    """Pruning owns what a schema edit invalidated. A constant is not read from
    the schema at all, so no edit can invalidate it."""
    mappings = InMemoryConceptMappingRepository()
    mappings.save(
        _mapping(
            reporter_tax_id="890903938",
            reporter_name="JFK Cooperativa Financiera",
            period="2025",
        )
    )

    PruneConceptMappings(KindRegistry([ExogenaReconciliation()]), mappings).execute(
        PruneConceptMappingsInput(document_type_id="type-1", extraction_schema=FULL_SCHEMA)
    )

    kept = mappings.get("type-1", KIND_ID)
    assert kept.reporter_name == "JFK Cooperativa Financiera"
    assert kept.period == "2025"


# --- Trimming the field that tells a table's rows apart ----------------------


def _row_mapping() -> ConceptMapping:
    """Two entries over one repeated field, told apart by what each row says."""
    return _mapping(
        entries=(
            ConceptMappingEntry(
                "cuentas[].saldo",
                SALDO,
                row_label_path="cuentas[].numero",
                row_label="Ahorros",
            ),
            ConceptMappingEntry("gmf", GMF),
        )
    )


def test_losing_the_field_that_names_each_row_drops_the_entry():
    """Not degraded to an undiscriminated entry: without the discriminator this
    entry would claim every row of the table, filing figures it was never given
    under its concept. A dropped entry is a gap the report shows; a silently
    widened one is a wrong answer nobody can see."""
    changes, pruned = _prune(_schema_without("cuentas[].numero"), _row_mapping())

    assert [e.field_path for e in pruned.entries] == ["gmf"]
    assert [c.change for c in changes] == [MappingChangeKind.ENTRY_DROPPED]
    assert changes[0].concept_id == SALDO


def test_an_edit_elsewhere_leaves_the_row_wording_untouched():
    _, pruned = _prune(_schema_without("razon_social"), _row_mapping())

    entry = next(e for e in pruned.entries if e.field_path == "cuentas[].saldo")
    assert (entry.row_label_path, entry.row_label) == ("cuentas[].numero", "Ahorros")
