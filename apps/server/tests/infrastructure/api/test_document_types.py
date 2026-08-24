from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from server.domain.entities import DocumentType
from server.infrastructure.api.auth_dependency import require_session
from server.infrastructure.api.deps import get_document_type_repository
from server.main import app


@pytest.fixture
def document_types():
    get_document_type_repository.cache_clear()
    yield get_document_type_repository()
    get_document_type_repository.cache_clear()


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[require_session] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


def _document_type(**overrides) -> DocumentType:
    defaults = dict(
        id="type-1",
        name="Bancolombia statement",
        description="Bank statement",
        extraction_prompt="Extract fields",
        extraction_schema={"type": "object", "properties": {}},
        active=True,
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return DocumentType(**defaults)


def test_list_document_types_defaults_to_active_only(client, document_types) -> None:
    document_types.save(_document_type(id="type-1", active=True))
    document_types.save(_document_type(id="type-2", active=False))

    response = client.get("/document-types")

    assert response.status_code == 200
    ids = [t["id"] for t in response.json()]
    assert ids == ["type-1"]


def test_list_document_types_with_active_only_false(client, document_types) -> None:
    document_types.save(_document_type(id="type-1", active=True))
    document_types.save(_document_type(id="type-2", active=False))

    response = client.get("/document-types", params={"active_only": "false"})

    assert response.status_code == 200
    ids = {t["id"] for t in response.json()}
    assert ids == {"type-1", "type-2"}


class _FailingMappingRepository:
    def save(self, mapping):
        raise RuntimeError("Firestore is unavailable")

    def get(self, document_type_id, kind_id):
        return None

    def list_for_kind(self, kind_id):
        return []


def test_a_mapping_that_cannot_be_stored_is_reported_not_raised() -> None:
    """The type is already saved and there is no transaction across the two
    contexts, so a 500 here would report an error while leaving the type
    created and hide that its mapping is missing."""
    from server.application.use_cases import DefinedDocumentType, DefineDocumentType
    from server.domain.ports import ProposedFieldMapping
    from server.infrastructure.api import deps
    from server.reconciliation.application import SaveConceptMapping

    document_type = DocumentType(
        id="t-1",
        name="Certificado",
        description="d",
        extraction_prompt="p",
        extraction_schema={"type": "object"},
        active=True,
        created_at=datetime.now(UTC),
    )

    class _UseCase(DefineDocumentType):
        def __init__(self):
            pass

        def execute(self, data):
            return DefinedDocumentType(
                document_type=document_type,
                field_mappings=(ProposedFieldMapping("saldo", "bank:cert_saldo_cuentas_ahorro"),),
                unmapped_fields=(),
                reporter_path="nit",
            )

    app.dependency_overrides[require_session] = lambda: None
    app.dependency_overrides[deps.get_define_document_type_use_case] = lambda: _UseCase()
    app.dependency_overrides[deps.get_save_concept_mapping_use_case] = lambda: SaveConceptMapping(
        deps.get_reconciliation_registry(), _FailingMappingRepository()
    )
    try:
        client = TestClient(app)
        response = client.post(
            "/document-types",
            json={
                "name": "Certificado",
                "description": "d",
                "extraction_prompt": "p",
                "extraction_schema": {"type": "object"},
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["field_mappings"] == []
        assert body["unmapped_fields"] == [
            {
                "field_path": "saldo",
                "reason": "the mapping could not be stored; set it again to retry",
            }
        ]
    finally:
        app.dependency_overrides.clear()


def test_a_mapping_with_no_reporting_party_is_not_stored() -> None:
    """Every fact needs a party to attribute it to, so the projection discards
    such a mapping whole. Storing it would leave the type looking configured
    and every claim reported as missing with nothing pointing at the cause."""
    from server.application.use_cases import DefinedDocumentType, DefineDocumentType
    from server.domain.ports import ProposedFieldMapping
    from server.infrastructure.api import deps

    document_type = DocumentType(
        id="t-2",
        name="Certificado",
        description="d",
        extraction_prompt="p",
        extraction_schema={"type": "object"},
        active=True,
        created_at=datetime.now(UTC),
    )

    class _UseCase(DefineDocumentType):
        def __init__(self):
            pass

        def execute(self, data):
            return DefinedDocumentType(
                document_type=document_type,
                field_mappings=(ProposedFieldMapping("saldo", "bank:cert_saldo_cuentas_ahorro"),),
                unmapped_fields=(),
                reporter_path=None,
            )

    deps.get_concept_mapping_repository.cache_clear()
    mappings = deps.get_concept_mapping_repository()
    app.dependency_overrides[require_session] = lambda: None
    app.dependency_overrides[deps.get_define_document_type_use_case] = lambda: _UseCase()
    try:
        response = TestClient(app).post(
            "/document-types",
            json={
                "name": "Certificado",
                "description": "d",
                "extraction_prompt": "p",
                "extraction_schema": {"type": "object"},
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["field_mappings"] == []
        assert body["unmapped_fields"] == [
            {
                "field_path": "saldo",
                "reason": "the document does not say who reports these amounts",
            }
        ]
        assert mappings.get("t-2", "exogena_dian") is None
    finally:
        app.dependency_overrides.clear()
        deps.get_concept_mapping_repository.cache_clear()


def test_a_type_that_declares_its_reporting_party_keeps_its_mappings() -> None:
    """The proposal names no reporter path because the paper never prints one.
    Discarding the mappings for that reason is the exact failure declaring the
    party exists to prevent."""
    from server.application.use_cases import DefinedDocumentType, DefineDocumentType
    from server.domain.ports import ProposedFieldMapping
    from server.infrastructure.api import deps

    document_type = DocumentType(
        id="t-3",
        name="Certificado JFK",
        description="d",
        extraction_prompt="p",
        extraction_schema={"type": "object"},
        active=True,
        created_at=datetime.now(UTC),
    )

    class _UseCase(DefineDocumentType):
        def __init__(self):
            pass

        def execute(self, data):
            return DefinedDocumentType(
                document_type=document_type,
                field_mappings=(ProposedFieldMapping("saldo", "bank:cert_saldo_cuentas_ahorro"),),
                unmapped_fields=(),
                reporter_path=None,
            )

    deps.get_concept_mapping_repository.cache_clear()
    mappings = deps.get_concept_mapping_repository()
    app.dependency_overrides[require_session] = lambda: None
    app.dependency_overrides[deps.get_define_document_type_use_case] = lambda: _UseCase()
    try:
        response = TestClient(app).post(
            "/document-types",
            json={
                "name": "Certificado JFK",
                "description": "d",
                "extraction_prompt": "p",
                "extraction_schema": {"type": "object"},
                "reporter_tax_id": "890903938",
                "reporter_name": "JFK Cooperativa Financiera",
            },
        )
        assert response.status_code == 201
        assert response.json()["unmapped_fields"] == []
        stored = mappings.get("t-3", "exogena_dian")
        assert stored is not None
        assert stored.reporter_tax_id == "890903938"
        assert [e.field_path for e in stored.entries] == ["saldo"]
    finally:
        app.dependency_overrides.clear()
        deps.get_concept_mapping_repository.cache_clear()


def test_a_declared_party_that_is_a_name_is_refused_before_anything_is_saved(
    client, document_types
) -> None:
    """Swallowed as a storage failure it read as "set it again to retry", which
    names neither what is wrong nor what to type instead — and left the type
    created with no mapping."""
    response = client.post(
        "/document-types",
        json={
            "name": "Certificado",
            "description": "d",
            "extraction_prompt": "p",
            "extraction_schema": {"type": "object"},
            "reporter_tax_id": "JFK Cooperativa Financiera",
        },
    )

    assert response.status_code == 422
    assert "not a tax id" in response.text
    assert document_types.list_all() == []


@pytest.fixture
def concept_mappings():
    from server.infrastructure.api import deps

    deps.get_concept_mapping_repository.cache_clear()
    yield deps.get_concept_mapping_repository()
    deps.get_concept_mapping_repository.cache_clear()


_TRIMMABLE_SCHEMA = {
    "type": "object",
    "properties": {
        "nit": {"type": "string"},
        "saldo": {"type": "string"},
        "gmf": {"type": "string"},
    },
}


def _mapping_for(document_type_id: str):
    from server.reconciliation.core.projection import ConceptMapping, ConceptMappingEntry

    return ConceptMapping(
        document_type_id=document_type_id,
        kind_id="exogena_dian",
        reporter_path="nit",
        entries=(
            ConceptMappingEntry("saldo", "bank:cert_saldo_cuentas_ahorro"),
            ConceptMappingEntry("gmf", "bank:cert_gmf_valor"),
        ),
    )


def test_editing_a_type_that_does_not_exist_is_a_404(client, document_types) -> None:
    response = client.patch("/document-types/ghost", json={"name": "Whatever"})

    assert response.status_code == 404


def test_an_edit_changes_only_the_fields_it_names(client, document_types) -> None:
    document_types.save(_document_type(id="type-1"))

    response = client.patch("/document-types/type-1", json={"name": "Certificado 2025"})

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Certificado 2025"
    assert body["description"] == "Bank statement"
    assert body["extraction_prompt"] == "Extract fields"
    assert body["mapping_changes"] == []


def test_trimming_the_schema_drops_the_mappings_it_orphaned(
    client, document_types, concept_mappings
) -> None:
    """The accountant only wants a few of the fields the AI proposed. Every
    mapping left pointing at a removed one would produce no fact and no error,
    so the claim behind it would read as missing evidence for no visible
    reason."""
    document_types.save(_document_type(id="type-1", extraction_schema=_TRIMMABLE_SCHEMA))
    concept_mappings.save(_mapping_for("type-1"))

    response = client.patch(
        "/document-types/type-1",
        json={
            "extraction_schema": {
                "type": "object",
                "properties": {"nit": {"type": "string"}, "saldo": {"type": "string"}},
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["mapping_changes"] == [
        {
            "kind_id": "exogena_dian",
            "change": "entry_dropped",
            "path": "gmf",
            "field_path": "gmf",
            "concept_id": "bank:cert_gmf_valor",
            "reason": "the schema no longer declares this field, so it can no longer be reconciled",
        }
    ]
    stored = concept_mappings.get("type-1", "exogena_dian")
    assert [e.field_path for e in stored.entries] == ["saldo"]


def test_dropping_the_reporting_party_field_clears_the_whole_mapping(
    client, document_types, concept_mappings
) -> None:
    """Without a reporting party no fact can be attributed to anyone, so what
    is left of the mapping is dead weight that still reads as configuration."""
    document_types.save(_document_type(id="type-1", extraction_schema=_TRIMMABLE_SCHEMA))
    concept_mappings.save(_mapping_for("type-1"))

    response = client.patch(
        "/document-types/type-1",
        json={"extraction_schema": {"type": "object", "properties": {"saldo": {"type": "string"}}}},
    )

    assert response.status_code == 200
    changes = response.json()["mapping_changes"]
    assert [c["change"] for c in changes] == ["mapping_cleared"]
    assert changes[0]["path"] == "nit"
    assert concept_mappings.get("type-1", "exogena_dian").entries == ()


def test_an_edit_that_leaves_the_schema_alone_never_touches_the_mappings(
    client, document_types, concept_mappings
) -> None:
    """Renaming a type must not cost it its mapping, so pruning only runs when
    the schema is the thing being edited."""
    document_types.save(_document_type(id="type-1", extraction_schema=_TRIMMABLE_SCHEMA))
    concept_mappings.save(_mapping_for("type-1"))

    response = client.patch("/document-types/type-1", json={"active": False})

    assert response.status_code == 200
    assert response.json()["mapping_changes"] == []
    assert len(concept_mappings.get("type-1", "exogena_dian").entries) == 2


def test_mappings_that_cannot_be_realigned_are_reported_not_raised(client, document_types) -> None:
    """The type is already saved, so a 500 would tell the caller the edit
    failed while leaving mappings pointing at fields that no longer exist."""
    from server.infrastructure.api import deps
    from server.reconciliation.application import PruneConceptMappings

    class _UnreadableMappingRepository(_FailingMappingRepository):
        def get(self, document_type_id, kind_id):
            raise RuntimeError("Firestore is unavailable")

    document_types.save(_document_type(id="type-1", extraction_schema=_TRIMMABLE_SCHEMA))
    app.dependency_overrides[deps.get_prune_concept_mappings_use_case] = lambda: (
        PruneConceptMappings(deps.get_reconciliation_registry(), _UnreadableMappingRepository())
    )

    response = client.patch(
        "/document-types/type-1",
        json={"extraction_schema": {"type": "object", "properties": {"nit": {"type": "string"}}}},
    )

    assert response.status_code == 200
    assert [c["change"] for c in response.json()["mapping_changes"]] == ["prune_failed"]


def test_the_tax_years_of_a_type_can_be_corrected(document_types, client) -> None:
    """A mistagged type would otherwise be uncorrectable, and every document it
    classifies would stay reported as covering another period."""
    document_types.save(
        DocumentType(
            id="t-years",
            name="Certificado",
            description="d",
            extraction_prompt="p",
            extraction_schema={"type": "object"},
            active=True,
            created_at=datetime.now(UTC),
            tax_years=(2023,),
        )
    )

    response = client.patch("/document-types/t-years", json={"tax_years": [2025]})

    assert response.status_code == 200
    assert response.json()["tax_years"] == [2025]
    assert document_types.get("t-years").tax_years == (2025,)


def test_clearing_the_tax_years_makes_a_type_apply_to_any_year(document_types, client) -> None:
    document_types.save(
        DocumentType(
            id="t-any",
            name="Certificado",
            description="d",
            extraction_prompt="p",
            extraction_schema={"type": "object"},
            active=True,
            created_at=datetime.now(UTC),
            tax_years=(2023, 2024),
        )
    )

    response = client.patch("/document-types/t-any", json={"tax_years": []})

    assert response.status_code == 200
    assert document_types.get("t-any").tax_years == ()


def test_omitting_the_tax_years_leaves_them_alone(document_types, client) -> None:
    document_types.save(
        DocumentType(
            id="t-keep",
            name="Certificado",
            description="d",
            extraction_prompt="p",
            extraction_schema={"type": "object"},
            active=True,
            created_at=datetime.now(UTC),
            tax_years=(2024,),
        )
    )

    client.patch("/document-types/t-keep", json={"name": "Otro nombre"})

    assert document_types.get("t-keep").tax_years == (2024,)


def test_a_field_keeps_what_it_said_on_the_sample(client, document_types) -> None:
    """The configurator screen shows the sample value beside every field, and
    the editor has to show the same one: a path and a label leave "which of
    these four figures is it?" open on a certificate that prints four."""
    created = client.post(
        "/document-types",
        json={
            "name": "Bancolombia GMF",
            "description": "Certificado GMF",
            "extraction_prompt": "Extract it",
            "extraction_schema": {"type": "object", "properties": {"gmf": {"type": "number"}}},
            "fields": [
                {
                    "path": "gmf",
                    "label": "Valor GMF",
                    "role": "amount",
                    "section": "Gravamen a los Movimientos Financieros",
                    "sample_value": "$ 512.561,52",
                }
            ],
        },
    )
    assert created.status_code == 201
    assert created.json()["fields"][0]["sample_value"] == "$ 512.561,52"

    # And on the way back out, which is the trip the editor actually makes.
    listed = client.get("/document-types").json()
    assert listed[0]["fields"][0]["sample_value"] == "$ 512.561,52"


def test_a_field_saved_before_sample_values_existed_still_reads(client, document_types) -> None:
    """Every type configured until now has none, and a missing value is a
    field described a little less well, never a type that fails to load."""
    created = client.post(
        "/document-types",
        json={
            "name": "Old type",
            "description": "Configured before",
            "extraction_prompt": "Extract it",
            "extraction_schema": {"type": "object", "properties": {"gmf": {"type": "number"}}},
            "fields": [{"path": "gmf", "label": "Valor GMF", "role": "amount"}],
        },
    )
    assert created.status_code == 201
    assert created.json()["fields"][0]["sample_value"] == ""


def test_field_descriptions_are_read_from_a_stored_document() -> None:
    """The endpoint the recovery uses: the type's own paths are the question,
    so an answer can only be about fields it actually declares."""
    from server.application.use_cases import (
        DescribeDocumentTypeFields,
        ReadStoredDocument,
    )
    from server.domain.ports import DocumentContent, FieldRole, ProposedField
    from server.infrastructure.api import deps

    class _Describe(DescribeDocumentTypeFields):
        def __init__(self):
            self.asked = None

        def execute(self, data):
            self.asked = data
            return (
                ProposedField("nit", "NIT del emisor", FieldRole.IDENTIFIER, "800150280", "Emisor"),
            )

    class _Read(ReadStoredDocument):
        def __init__(self):
            pass

        def execute(self, data):
            return DocumentContent(data=b"%PDF-", mime_type="application/pdf", file_name="c.pdf")

    describe = _Describe()
    app.dependency_overrides[require_session] = lambda: None
    app.dependency_overrides[deps.get_describe_document_type_fields_use_case] = lambda: describe
    app.dependency_overrides[deps.get_read_stored_document_use_case] = lambda: _Read()
    try:
        response = TestClient(app).post(
            "/document-types/type-1/field-descriptions",
            data={"document_id": "doc-1"},
        )
        assert response.status_code == 200
        assert response.json()["fields"] == [
            {
                "path": "nit",
                "label": "NIT del emisor",
                "role": "identifier",
                "sample_value": "800150280",
                "section": "Emisor",
            }
        ]
        assert describe.asked.document_type_id == "type-1"
    finally:
        app.dependency_overrides.clear()


def test_describing_the_fields_of_a_type_that_is_gone_is_a_404() -> None:
    from server.application.use_cases import DescribeDocumentTypeFields, ReadStoredDocument
    from server.application.use_cases.update_document_type import DocumentTypeNotFound
    from server.domain.ports import DocumentContent
    from server.infrastructure.api import deps

    class _Describe(DescribeDocumentTypeFields):
        def __init__(self):
            pass

        def execute(self, data):
            raise DocumentTypeNotFound("gone")

    class _Read(ReadStoredDocument):
        def __init__(self):
            pass

        def execute(self, data):
            return DocumentContent(data=b"%PDF-", mime_type="application/pdf", file_name="c.pdf")

    app.dependency_overrides[require_session] = lambda: None
    app.dependency_overrides[deps.get_describe_document_type_fields_use_case] = lambda: _Describe()
    app.dependency_overrides[deps.get_read_stored_document_use_case] = lambda: _Read()
    try:
        response = TestClient(app).post(
            "/document-types/gone/field-descriptions", data={"document_id": "doc-1"}
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
