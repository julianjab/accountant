from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from server.reconciliation.application.ports import ConceptMappingRepository
from server.reconciliation.core.projection import (
    ConceptMapping,
    ConceptMappingEntry,
    path_resolves_in,
)
from server.reconciliation.core.registry import KindRegistry


class MappingChangeKind(StrEnum):
    """What pruning did to a mapping, so the caller can say it in one line."""

    ENTRY_DROPPED = "entry_dropped"
    PATH_CLEARED = "path_cleared"
    MAPPING_CLEARED = "mapping_cleared"
    #: Pruning itself could not run. Reported like the rest so a storage
    #: failure never reads as "nothing needed changing".
    PRUNE_FAILED = "prune_failed"


@dataclass(frozen=True, slots=True)
class MappingChange:
    kind_id: str
    change: MappingChangeKind
    reason: str
    #: The path in the old mapping that stopped resolving.
    path: str | None = None
    #: The entry affected, when the change concerns a single one.
    field_path: str | None = None
    concept_id: str | None = None


@dataclass(frozen=True, slots=True)
class PruneConceptMappingsInput:
    document_type_id: str
    extraction_schema: dict[str, Any]


class PruneConceptMappings:
    """Realigns a document type's concept mappings with an edited schema.

    A mapping entry points at a path in the extraction schema. Trim that field
    away and the entry survives pointing at nothing: the projection resolves it
    to no value, so it emits no fact, silently. The type still looks configured
    and its mappings still show in the UI, while the claim they were meant to
    satisfy is reported as missing evidence with nothing anywhere naming the
    cause — which is the single hardest failure in this product to trace back.

    So the dead entries are removed as part of the edit and returned, so the
    person who trimmed the schema learns what they gave up while they still
    remember why they trimmed it.
    """

    def __init__(self, registry: KindRegistry, mappings: ConceptMappingRepository) -> None:
        self._registry = registry
        self._mappings = mappings

    def execute(self, data: PruneConceptMappingsInput) -> tuple[MappingChange, ...]:
        changes: list[MappingChange] = []
        for kind in self._registry.all():
            mapping = self._mappings.get(data.document_type_id, kind.id)
            if mapping is None:
                continue
            pruned, kind_changes = _prune(mapping, data.extraction_schema)
            if kind_changes:
                self._mappings.save(pruned)
                changes.extend(kind_changes)
        return tuple(changes)


def _prune(
    mapping: ConceptMapping, schema: dict[str, Any]
) -> tuple[ConceptMapping, list[MappingChange]]:
    changes: list[MappingChange] = []

    if mapping.reporter_path is not None and not path_resolves_in(mapping.reporter_path, schema):
        # Without a reporting party no fact can be attributed to anyone, so the
        # projection discards this mapping whole however many entries survive.
        # Keeping the entries would leave the type looking mapped while nothing
        # it extracts ever reaches a report.
        return (
            ConceptMapping(
                document_type_id=mapping.document_type_id,
                kind_id=mapping.kind_id,
                entries=(),
            ),
            [
                MappingChange(
                    kind_id=mapping.kind_id,
                    change=MappingChangeKind.MAPPING_CLEARED,
                    path=mapping.reporter_path,
                    reason=(
                        "the schema no longer extracts who reports these amounts, so no fact "
                        "could be attributed to anyone; the whole mapping was cleared"
                    ),
                )
            ],
        )

    document_paths: dict[str, str | None] = {
        "reporter_name_path": mapping.reporter_name_path,
        "period_path": mapping.period_path,
    }
    for name, path in document_paths.items():
        if path is not None and not path_resolves_in(path, schema):
            document_paths[name] = None
            changes.append(
                MappingChange(
                    kind_id=mapping.kind_id,
                    change=MappingChangeKind.PATH_CLEARED,
                    path=path,
                    reason=f"the schema no longer declares this field, so {name} was cleared",
                )
            )

    entries: list[ConceptMappingEntry] = []
    for entry in mapping.entries:
        if not path_resolves_in(entry.field_path, schema):
            changes.append(
                MappingChange(
                    kind_id=mapping.kind_id,
                    change=MappingChangeKind.ENTRY_DROPPED,
                    path=entry.field_path,
                    field_path=entry.field_path,
                    concept_id=entry.concept_id,
                    reason=(
                        "the schema no longer declares this field, so it can no longer be "
                        "reconciled"
                    ),
                )
            )
            continue
        account_path = entry.account_path
        if account_path is not None and not path_resolves_in(account_path, schema):
            # The amount still reconciles; it just can no longer be tied to an
            # account, which only weakens matching rather than losing the fact.
            account_path = None
            changes.append(
                MappingChange(
                    kind_id=mapping.kind_id,
                    change=MappingChangeKind.PATH_CLEARED,
                    path=entry.account_path,
                    field_path=entry.field_path,
                    concept_id=entry.concept_id,
                    reason=(
                        "the schema no longer declares this field, so the amount is no longer "
                        "tied to an account"
                    ),
                )
            )
        entries.append(
            ConceptMappingEntry(
                field_path=entry.field_path,
                concept_id=entry.concept_id,
                account_path=account_path,
                sign=entry.sign,
            )
        )

    pruned = ConceptMapping(
        document_type_id=mapping.document_type_id,
        kind_id=mapping.kind_id,
        entries=tuple(entries),
        reporter_path=mapping.reporter_path,
        reporter_name_path=document_paths["reporter_name_path"],
        period_path=document_paths["period_path"],
    )
    return pruned, changes
