"""Every adapter implements the whole port it stands behind.

Protocols are structural and unchecked at runtime, so an adapter can be missing
a method and nothing notices until a request hits it. That is what happened to
FirestoreDocumentTypeRepository.list_all: the tests all exercised the in-memory
adapter, which had it, and the inbox raised AttributeError in production.

This walks the pairs instead of trusting that each one was remembered.
"""

import pytest

from server.domain import ports
from server.infrastructure.adapters import firestore_repositories, in_memory_repositories
from server.reconciliation.application import ports as reconciliation_ports
from server.reconciliation.infrastructure import (
    firestore_repositories as reconciliation_firestore,
)
from server.reconciliation.infrastructure import in_memory_repositories as reconciliation_memory

_INTAKE = [
    (ports.ClientRepository, "ClientRepository"),
    (ports.DocumentRepository, "DocumentRepository"),
    (ports.DocumentTypeRepository, "DocumentTypeRepository"),
    (ports.ExtractedDataRepository, "ExtractedDataRepository"),
    (ports.SessionRepository, "SessionRepository"),
    (ports.DriveWatchChannelRepository, "DriveWatchChannelRepository"),
    (ports.DriveFileClaimRepository, "DriveFileClaimRepository"),
]

_RECONCILIATION = [
    (reconciliation_ports.ConceptMappingRepository, "ConceptMappingRepository"),
    (reconciliation_ports.ReconciliationReportRepository, "ReconciliationReportRepository"),
]

_CASES = [
    *[(p, firestore_repositories, "Firestore", n) for p, n in _INTAKE],
    *[(p, in_memory_repositories, "InMemory", n) for p, n in _INTAKE],
    *[(p, reconciliation_firestore, "Firestore", n) for p, n in _RECONCILIATION],
    *[(p, reconciliation_memory, "InMemory", n) for p, n in _RECONCILIATION],
]


def _required(protocol) -> set[str]:
    return {
        name
        for name in dir(protocol)
        if not name.startswith("_") and callable(getattr(protocol, name, None))
    }


@pytest.mark.parametrize(
    ("protocol", "module", "prefix", "suffix"),
    _CASES,
    ids=[f"{prefix}{suffix}" for _, _, prefix, suffix in _CASES],
)
def test_adapter_implements_every_port_method(protocol, module, prefix, suffix) -> None:
    adapter = getattr(module, f"{prefix}{suffix}")
    missing = sorted(_required(protocol) - {n for n in dir(adapter) if not n.startswith("_")})
    assert not missing, f"{prefix}{suffix} is missing {missing}"
