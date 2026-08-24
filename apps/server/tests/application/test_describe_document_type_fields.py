"""Re-reading a sample to name the fields a type already declares."""

from datetime import UTC, datetime

import pytest

from server.application.use_cases import (
    DescribeDocumentTypeFields,
    DescribeDocumentTypeFieldsInput,
)
from server.application.use_cases.update_document_type import DocumentTypeNotFound
from server.domain.entities import DocumentType
from server.domain.ports import DocumentContent, FieldRole, ProposedField

SAMPLE = DocumentContent(data=b"%PDF-", mime_type="application/pdf", file_name="cert.pdf")

SCHEMA = {
    "type": "object",
    "properties": {
        "nit": {"type": "string"},
        "cuentas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"numero": {"type": "string"}, "saldo": {"type": "number"}},
            },
        },
    },
}


class _Configurator:
    def __init__(self, fields=()) -> None:
        self.asked: tuple = ()
        self.type_name = ""
        self._fields = fields

    def propose_config(self, content, type_name, concepts=()):  # pragma: no cover - unused
        raise AssertionError("describing must not propose a fresh configuration")

    def describe_fields(self, content, type_name, paths):
        self.asked = tuple(paths)
        self.type_name = type_name
        return self._fields


class _Repository:
    def __init__(self, document_type: DocumentType | None) -> None:
        self._document_type = document_type

    def get(self, document_type_id):
        return self._document_type


def _document_type(**overrides) -> DocumentType:
    defaults = dict(
        id="type-1",
        name="Certificado Fiduciaria",
        description="",
        extraction_prompt="Extract it.",
        extraction_schema=SCHEMA,
        active=True,
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return DocumentType(**defaults)


def test_the_type_s_own_paths_are_what_gets_asked_about():
    """The repair itself: a proposal run names its fields afresh and matches
    the stored schema only by luck, so nothing could be recovered from it."""
    configurator = _Configurator()

    DescribeDocumentTypeFields(_Repository(_document_type()), configurator).execute(
        DescribeDocumentTypeFieldsInput(document_type_id="type-1", document=SAMPLE)
    )

    assert configurator.asked == ("nit", "cuentas[].numero", "cuentas[].saldo")
    assert configurator.type_name == "Certificado Fiduciaria"


def test_the_descriptions_are_returned_and_nothing_is_stored():
    described = (ProposedField("nit", "NIT", FieldRole.IDENTIFIER, "800150280", "Encabezado"),)
    configurator = _Configurator(described)

    fields = DescribeDocumentTypeFields(_Repository(_document_type()), configurator).execute(
        DescribeDocumentTypeFieldsInput(document_type_id="type-1", document=SAMPLE)
    )

    assert fields == described


def test_an_unknown_type_is_refused_rather_than_read():
    with pytest.raises(DocumentTypeNotFound):
        DescribeDocumentTypeFields(_Repository(None), _Configurator()).execute(
            DescribeDocumentTypeFieldsInput(document_type_id="gone", document=SAMPLE)
        )
