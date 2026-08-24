from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from server.shared import (
    AccountRef,
    FactRole,
    FinancialFact,
    Money,
    Period,
    PeriodGranularity,
    TaxId,
)

_INDEX = re.compile(r"\[(\d+)\]")
_SEGMENT = re.compile(r"^([^\[\]]*)((?:\[\d+\])*)$")


@dataclass(frozen=True, slots=True)
class ConceptMappingEntry:
    """Maps one extracted field onto a concept the engine can reconcile."""

    #: Dotted path into the extracted fields. A segment may end in `[]` to walk
    #: a list, which is what lets one certificate disclose several accounts.
    field_path: str
    concept_id: str
    #: Where the account identifier for this amount lives. Resolved in the same
    #: iteration as `field_path`, so `accounts[].number` pairs element-wise
    #: with `accounts[].balance`.
    account_path: str | None = None
    sign: int = 1

    def __post_init__(self) -> None:
        # A sign of 0 would silently zero every amount this field contributes
        # and a 2 would double it, with nothing downstream to notice. These
        # values arrive from an AI proposal and from an HTTP payload, so the
        # entity itself refuses anything else.
        if self.sign not in (1, -1):
            raise ValueError(f"A concept mapping's sign must be +1 or -1, not {self.sign}")


@dataclass(frozen=True, slots=True)
class ConceptMapping:
    """Turns a document type's extraction schema into reconcilable facts.

    This is the one place the two halves of the product meet. Extraction stays
    faithful to whatever the document actually says — that is what the
    accountant reviews — and this projects it into the shared vocabulary. It is
    plain configuration rather than a second AI pass on purpose: a mapping the
    accountant can read is a mapping they can be held to.
    """

    document_type_id: str
    kind_id: str
    entries: tuple[ConceptMappingEntry, ...]
    #: Where the reporting party's identifier sits, when the document states it.
    reporter_path: str | None = None
    reporter_name_path: str | None = None
    #: Where the document states the period it covers. Without it a 2024
    #: certificate uploaded into a 2025 reconciliation would be taken at the
    #: caller's word and quietly reconcile against the wrong year.
    period_path: str | None = None


def project_facts(
    mapping: ConceptMapping,
    fields: Mapping[str, Any],
    *,
    source_id: str,
    period: Period,
    subject_tax_id: TaxId | None = None,
    reporter_tax_id: TaxId | None = None,
    reporter_name: str = "",
    locator: str = "",
) -> tuple[FinancialFact, ...]:
    resolved_reporter = _first_tax_id(fields, mapping.reporter_path) or reporter_tax_id
    if resolved_reporter is None:
        raise ValueError(
            f"Cannot project {mapping.document_type_id}: no reporting party on the document "
            "and none supplied by the caller"
        )
    resolved_name = _first_text(fields, mapping.reporter_name_path) or reporter_name
    resolved_period = _period_from(fields, mapping.period_path, period) or period

    facts: list[FinancialFact] = []
    for entry in mapping.entries:
        for value, indices in _resolve(fields, entry.field_path):
            amount = Money.parse(value)
            # A field the document did not state is not a zero. Emitting zeros
            # here would turn "the bank never mentioned this" into "the bank
            # says it is nil", which reconciles against nothing and hides the
            # gap the report exists to show.
            if amount is None:
                continue
            account = None
            if entry.account_path is not None:
                account = _first_account(fields, _with_indices(entry.account_path, indices))
            facts.append(
                FinancialFact(
                    source_id=source_id,
                    role=FactRole.EVIDENCE,
                    reporter_tax_id=resolved_reporter,
                    reporter_name=resolved_name,
                    subject_tax_id=subject_tax_id,
                    concept_id=entry.concept_id,
                    period=resolved_period,
                    amount=amount * entry.sign,
                    account=account,
                    detail=entry.field_path,
                    locator=locator,
                )
            )
    return tuple(facts)


def path_resolves_in(path: str, schema: object) -> bool:
    """Whether a dotted path points at something an extraction schema declares.

    Walks `properties`, and `items` for a `[]` segment. A schema that declares
    no properties cannot be checked against, so the path is accepted there:
    rejecting every mapping would be worse than the gap this closes.

    It lives beside `project_facts` because this is the static counterpart of
    what `_walk` does at runtime: both answer "does this path lead anywhere",
    one against the schema and one against the extracted values. Keeping them
    apart is how a mapping stays accepted that the projection then ignores.
    """
    if not isinstance(schema, dict) or not isinstance(schema.get("properties"), dict):
        return True
    node: object = schema
    for segment in path.split("."):
        iterate = segment.endswith("[]")
        key = segment[:-2] if iterate else segment
        properties = node.get("properties") if isinstance(node, dict) else None
        if not isinstance(properties, dict) or key not in properties:
            return False
        node = properties[key]
        if iterate:
            if not isinstance(node, dict) or node.get("type") != "array":
                return False
            node = node.get("items", {})
    return True


def _resolve(node: Any, path: str) -> list[tuple[Any, tuple[int, ...]]]:
    """Walk a dotted path, returning each value with the list indices reached."""
    return _walk(node, [s for s in path.split(".") if s], ())


def _walk(
    node: Any, segments: list[str], indices: tuple[int, ...]
) -> list[tuple[Any, tuple[int, ...]]]:
    if not segments:
        return [(node, indices)]
    segment, rest = segments[0], segments[1:]
    iterate = segment.endswith("[]")
    key = segment[:-2] if iterate else segment
    if key:
        if not isinstance(node, Mapping) or key not in node:
            return []
        node = node[key]
    if not iterate:
        return _walk(node, rest, indices)
    if not isinstance(node, Sequence) or isinstance(node, str | bytes):
        return []
    found: list[tuple[Any, tuple[int, ...]]] = []
    for position, item in enumerate(node):
        found.extend(_walk(item, rest, (*indices, position)))
    return found


def _with_indices(path: str, indices: tuple[int, ...]) -> str:
    """Pin a sibling path to the same list positions the value came from."""
    remaining = list(indices)
    parts = path.split("[]")
    rebuilt = parts[0]
    for part in parts[1:]:
        rebuilt += f"[{remaining.pop(0)}]" if remaining else "[]"
        rebuilt += part
    return rebuilt


def _lookup(fields: Mapping[str, Any], path: str | None) -> Any:
    """Read a single value at a fully-resolved path (`accounts[0].number`)."""
    if not path:
        return None
    node: Any = fields
    for segment in path.split("."):
        match = _SEGMENT.match(segment)
        if match is None:
            return None
        key, subscripts = match.group(1), match.group(2)
        if key:
            if not isinstance(node, Mapping) or key not in node:
                return None
            node = node[key]
        for raw_index in _INDEX.findall(subscripts):
            index = int(raw_index)
            if not isinstance(node, Sequence) or isinstance(node, str | bytes):
                return None
            if index >= len(node):
                return None
            node = node[index]
    return node


def _period_from(fields: Mapping[str, Any], path: str | None, fallback: Period) -> Period | None:
    """Read the period the document itself states, when it states one.

    Only yearly periods are recoverable from a single field today; anything
    finer falls back to the caller's period rather than guessing a month.
    """
    if fallback.granularity is not PeriodGranularity.YEAR:
        return None
    raw = _lookup(fields, path)
    if raw is None:
        return None
    match = re.search(r"\b(19|20)\d{2}\b", str(raw))
    return Period.of_year(int(match.group(0))) if match else None


def _first_tax_id(fields: Mapping[str, Any], path: str | None) -> TaxId | None:
    value = _lookup(fields, path)
    return TaxId.parse(value) if value is not None else None


def _first_text(fields: Mapping[str, Any], path: str | None) -> str:
    value = _lookup(fields, path)
    return "" if value is None else str(value).strip()


def _first_account(fields: Mapping[str, Any], path: str) -> AccountRef | None:
    value = _lookup(fields, path)
    return AccountRef.parse(value) if value is not None else None
