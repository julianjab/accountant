"""Listing the paths a document type's schema declares."""

from server.domain.extraction_schema import list_schema_paths


def test_listing_a_schema_s_paths_walks_into_objects_and_lists():
    """What paths there are, so a re-reading of a sample can be asked about
    the fields a type already declares."""
    schema = {
        "type": "object",
        "properties": {
            "nit": {"type": "string"},
            "emisor": {"type": "object", "properties": {"nombre": {"type": "string"}}},
            "cuentas": {
                "type": "array",
                "items": {"type": "object", "properties": {"saldo": {"type": "number"}}},
            },
        },
    }

    assert list_schema_paths(schema) == ("nit", "emisor.nombre", "cuentas[].saldo")


def test_a_schema_that_declares_nothing_lists_nothing():
    assert list_schema_paths({"type": "object"}) == ()
    assert list_schema_paths("not a schema") == ()
