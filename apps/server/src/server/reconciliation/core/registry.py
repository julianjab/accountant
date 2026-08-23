from __future__ import annotations

from collections.abc import Iterable

from server.reconciliation.core.kind import ReconciliationKind


class UnknownReconciliationKind(KeyError):
    pass


class KindRegistry:
    """The one place that knows which reconciliation models exist.

    It is handed its kinds rather than importing them, so this module — and
    everything else in core — stays unaware of the DIAN or any other model.
    Composition happens once, at application startup.
    """

    def __init__(self, kinds: Iterable[ReconciliationKind] = ()) -> None:
        self._by_id: dict[str, ReconciliationKind] = {}
        for kind in kinds:
            self.register(kind)

    def register(self, kind: ReconciliationKind) -> None:
        if kind.id in self._by_id:
            raise ValueError(f"Reconciliation kind already registered: {kind.id}")
        self._by_id[kind.id] = kind

    def get(self, kind_id: str) -> ReconciliationKind:
        try:
            return self._by_id[kind_id]
        except KeyError as exc:
            raise UnknownReconciliationKind(kind_id) from exc

    def all(self) -> tuple[ReconciliationKind, ...]:
        return tuple(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)
