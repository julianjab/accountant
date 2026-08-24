"""Offers a reconciliation kind's own parsers to document intake.

The second composition edge, alongside `DocumentFactProvider`: intake must be
able to say "this file is a DIAN exogena report" without importing the DIAN,
and reconciliation must keep owning the parser. This module knows both sides so
neither has to.

Without it a parser-owned file is a dead end on screen. Reconciliation already
reads it whatever intake made of it, so the figures were never actually
missing — but the document sits there FAILED with "could not identify the
document type", which reads as *nothing was read from this file*, and there is
no way to say otherwise or to approve it.
"""

from __future__ import annotations

import logging
from collections import Counter
from decimal import Decimal

from server.domain.ports import DocumentContent, ParsableSource, ParsedSource, SourceNotParsable
from server.reconciliation.core.kind import (
    FactSourceSpec,
    SourceContent,
    SourceNotRecognized,
)
from server.reconciliation.core.registry import KindRegistry
from server.shared import FinancialFact, Money

logger = logging.getLogger(__name__)


class KindSourceParsers:
    """Implements `domain.ports.DocumentSourceParsers` over the registered kinds."""

    def __init__(self, registry: KindRegistry) -> None:
        self._registry = registry

    def available(self) -> tuple[ParsableSource, ...]:
        return tuple(
            ParsableSource(id=source.id, label=source.label, media_types=source.media_types)
            for source in self._sources()
        )

    def parse(self, content: DocumentContent, source_id: str) -> ParsedSource:
        source = next((s for s in self._sources() if s.id == source_id), None)
        if source is None:
            raise SourceNotParsable(f"No parser is registered for source {source_id!r}")
        if content.mime_type not in source.media_types:
            raise SourceNotParsable(f"A {source.label} is not a {content.mime_type} file")

        try:
            # The file states its own period and reporting parties; nothing here
            # supplies them, so a wrong guess by the caller cannot end up
            # stamped on the facts.
            facts = source.extractor.extract(
                SourceContent(
                    data=content.data,
                    media_type=content.mime_type,
                    file_name=content.file_name,
                    source_id=source_id,
                )
            )
        except SourceNotRecognized as exc:
            # An ordinary outcome: a client's folder holds all sorts of
            # spreadsheets, and this one is not the report it was said to be.
            raise SourceNotParsable(str(exc)) from exc
        except Exception as exc:
            # Everything else a parser can do with bytes a person chose: a
            # malformed report, or a file that is not a workbook at all. The
            # failures come out of whichever library reads the format
            # (`BadZipFile`, `InvalidFileException`, an IndexError deep in a
            # sheet), and enumerating those here would mean this adapter has to
            # be edited every time a parser changes its dependencies — while a
            # missed one reaches the caller as a 500 for a file they simply
            # named wrong. Logged with the traceback so a genuine defect is
            # still visible rather than swallowed.
            logger.exception(
                "Could not read a document as the source it was declared to be",
                extra={"source_id": source_id, "file_name": content.file_name},
            )
            raise SourceNotParsable(
                f"This file could not be read as a {source.label}: {exc}"
            ) from exc

        logger.info(
            "Recognised a document as a parsed source",
            extra={"source_id": source_id, "facts": len(facts)},
        )
        return ParsedSource(
            source_id=source_id,
            summary=_summarise(facts),
            periods=tuple(sorted({fact.period.key for fact in facts})),
        )

    def _sources(self) -> tuple[FactSourceSpec, ...]:
        return tuple(
            source
            for kind in self._registry.all()
            for source in kind.sources()
            if source.extractor is not None
        )


def _summarise(facts: tuple[FinancialFact, ...]) -> dict[str, object]:
    """What a reviewer needs to tell that the right file was read.

    A count and a total, not the rows: the report runs to thousands of them and
    they already reach reconciliation straight from the file. Seeing the tax
    year and the parties is what confirms this is the client's report for the
    year in hand — the one thing a person cannot check by trusting the parser.
    """
    if not facts:
        return {"reported_rows": 0}

    periods = sorted({fact.period.key for fact in facts})
    reporters = Counter(fact.reporter_name or fact.reporter_tax_id.value for fact in facts)
    total = sum((fact.amount for fact in facts), Money.zero())
    return {
        "reported_rows": len(facts),
        "periods": periods,
        "reporting_parties": len(reporters),
        "total_reported": _as_number(total),
        # The handful of parties that account for most of the report, so the
        # reviewer recognises the file rather than merely counting it.
        "top_reporting_parties": [name for name, _ in reporters.most_common(5)],
    }


def _as_number(amount: Money) -> float | int:
    """Money as JSON, keeping whole pesos whole.

    The exogena rounds every figure to the peso; rendering those as `1234.0`
    invites a reader to wonder what the decimals were hiding.
    """
    if amount.amount == amount.amount.to_integral_value():
        return int(amount.amount)
    return float(amount.amount.quantize(Decimal("0.01")))
