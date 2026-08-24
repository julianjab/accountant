"""The reconciliation HTTP surface."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from server.domain.entities import Client
from server.infrastructure.api import deps
from server.infrastructure.api.auth_dependency import require_session
from server.main import app
from server.reconciliation.application import ReconcileClientPeriod
from server.reconciliation.core.contribution import GatheredFacts
from server.reconciliation.kinds.exogena import KIND_ID

NOW = datetime.now(UTC)
BASE = f"/reconciliation/kinds/{KIND_ID}"


@pytest.fixture
def clients():
    deps.get_client_repository.cache_clear()
    yield deps.get_client_repository()
    deps.get_client_repository.cache_clear()


@pytest.fixture
def mappings():
    deps.get_concept_mapping_repository.cache_clear()
    yield deps.get_concept_mapping_repository()
    deps.get_concept_mapping_repository.cache_clear()


@pytest.fixture
def reports():
    deps.get_reconciliation_report_repository.cache_clear()
    yield deps.get_reconciliation_report_repository()
    deps.get_reconciliation_report_repository.cache_clear()


class _NoFacts:
    """Stands in for the document-backed fact provider.

    Without it these tests fell through to the real one, which builds
    GoogleDriveStorage from the developer's service-account file — reaching a
    live Drive from a unit test, and failing outright on a machine with no
    credentials. Overriding the use case rather than the storage is what works
    here: deps builds the provider by calling its factories directly, so
    FastAPI's dependency_overrides never sees them.
    """

    def facts_for(self, client_id, period, kind_id):
        return GatheredFacts(facts=())


@pytest.fixture
def client(clients, mappings, reports) -> TestClient:
    deps.get_document_repository.cache_clear()
    app.dependency_overrides[require_session] = lambda: None
    app.dependency_overrides[deps.get_reconcile_client_period_use_case] = lambda: (
        ReconcileClientPeriod(deps.get_reconciliation_registry(), _NoFacts(), reports)
    )
    clients.save(
        Client(id="c1", name="Contribuyente", tax_id="79999999", email=None, created_at=NOW)
    )
    yield TestClient(app)
    app.dependency_overrides.clear()
    deps.get_document_repository.cache_clear()


def test_kinds_publish_the_vocabulary_a_client_needs_to_render_them(client):
    """So the web app never has to know which reconciliation model it shows."""
    response = client.get("/reconciliation/kinds")
    assert response.status_code == 200
    kinds = response.json()
    assert [k["id"] for k in kinds] == [KIND_ID]
    assert kinds[0]["period_granularity"] == "year"
    assert any(c["id"] == "dian:saldo-cuentas-bancarias" for c in kinds[0]["spine_concepts"])
    assert any(c["id"] == "bank:cert_saldo_cuentas_ahorro" for c in kinds[0]["evidence_concepts"])


def test_a_single_kind_can_be_read(client):
    assert client.get(f"{BASE}").json()["id"] == KIND_ID


def test_an_unknown_kind_is_a_404(client):
    assert client.get("/reconciliation/kinds/bank_statement").status_code == 404
    assert client.get("/reconciliation/kinds/nope/clients/c1/periods/2025").status_code == 404


def test_reading_before_any_run_says_so_rather_than_reconciling(client):
    """A read that silently ran the engine would hide the answer the caller
    needs: nothing has been reconciled yet."""
    assert client.get(f"{BASE}/clients/c1/periods/2025").status_code == 404


def test_running_a_reconciliation_returns_a_report_that_can_be_read_back(client):
    run = client.post(f"{BASE}/clients/c1/periods/2025")
    assert run.status_code == 200
    body = run.json()
    assert body["client_id"] == "c1"
    assert body["period"] == "2025"
    assert body["summary"]["total_findings"] == len(body["findings"])

    read = client.get(f"{BASE}/clients/c1/periods/2025")
    assert read.status_code == 200
    assert read.json()["id"] == body["id"]


def test_rerunning_replaces_the_report_instead_of_adding_another(client):
    first = client.post(f"{BASE}/clients/c1/periods/2025").json()
    second = client.post(f"{BASE}/clients/c1/periods/2025").json()
    assert first["id"] == second["id"]


@pytest.mark.parametrize("period", ["20xx", "2025-13", "2025-1", "", "abc"])
def test_a_malformed_period_is_rejected(client, period):
    response = client.post(f"{BASE}/clients/c1/periods/{period}")
    assert response.status_code in (404, 422)


def test_a_period_of_the_wrong_granularity_is_rejected(client):
    """The exogena is annual; asking for a month is a caller bug, not an empty
    report."""
    response = client.post(f"{BASE}/clients/c1/periods/2025-03")
    assert response.status_code == 422
    assert "reconciles by" in response.json()["detail"]


def test_a_concept_mapping_round_trips(client):
    payload = {
        "reporter_path": "agente_retenedor_nit",
        "reporter_name_path": "agente_retenedor_nombre",
        "period_path": "ano_gravable",
        "entries": [
            {"field_path": "saldo_cuenta_ahorros", "concept_id": "bank:cert_saldo_cuentas_ahorro"},
            {"field_path": "cargo", "concept_id": "bank:cert_cartera_otros", "sign": -1},
        ],
    }
    saved = client.put(f"{BASE}/document-types/type-1/mapping", json=payload)
    assert saved.status_code == 200
    assert saved.json()["document_type_id"] == "type-1"

    read = client.get(f"{BASE}/document-types/type-1/mapping")
    assert read.status_code == 200
    assert read.json()["entries"] == saved.json()["entries"]
    assert read.json()["period_path"] == "ano_gravable"


def test_an_unmapped_document_type_is_a_404(client):
    assert client.get(f"{BASE}/document-types/unmapped/mapping").status_code == 404


def test_a_mapping_naming_an_unknown_concept_is_refused(client):
    """A typo would otherwise be stored, produce facts no rule selects, and
    leave the claim it was meant to satisfy reported as missing with nothing
    pointing at the mapping."""
    response = client.put(
        f"{BASE}/document-types/type-1/mapping",
        json={"entries": [{"field_path": "saldo", "concept_id": "bank:typo"}]},
    )
    assert response.status_code == 422
    assert "bank:typo" in response.json()["detail"]


def test_a_mapping_for_an_unknown_kind_is_a_404(client):
    response = client.put(
        "/reconciliation/kinds/nope/document-types/type-1/mapping",
        json={"entries": []},
    )
    assert response.status_code == 404


def test_a_sign_outside_plus_or_minus_one_is_rejected(client):
    response = client.put(
        f"{BASE}/document-types/type-1/mapping",
        json={"entries": [{"field_path": "s", "concept_id": "bank:cert_gmf_valor", "sign": 3}]},
    )
    assert response.status_code == 422


def test_every_endpoint_requires_a_session():
    """Only /health and the Drive webhook are open."""
    app.dependency_overrides.clear()
    unauthenticated = TestClient(app)
    for method, path in (
        ("get", "/reconciliation/kinds"),
        ("get", f"{BASE}/clients/c1/periods/2025"),
        ("post", f"{BASE}/clients/c1/periods/2025"),
        ("get", f"{BASE}/document-types/type-1/mapping"),
    ):
        response = getattr(unauthenticated, method)(path)
        assert response.status_code == 401, path
