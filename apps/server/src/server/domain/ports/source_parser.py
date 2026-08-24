from dataclasses import dataclass
from typing import Any, Protocol

from server.domain.ports.document_storage import DocumentContent


@dataclass(frozen=True, slots=True)
class ParsableSource:
    """A document format something in this application can read on its own.

    Distinct from a `DocumentType`, which is a *configuration* — a prompt and a
    schema an AI applies. These are formats with a parser behind them: exact,
    free, and the same on every run. A screen offers them so a person can say
    what a file is when the classifier could not, and a classifier has nothing
    to match against because such a format is deliberately not configured as a
    document type.
    """

    id: str
    label: str
    #: The media types the parser accepts, so a screen can offer only the
    #: sources that could plausibly read the file in front of the reader.
    media_types: frozenset[str]


@dataclass(frozen=True, slots=True)
class ParsedSource:
    source_id: str
    #: What was read, summarised for display. Deliberately a summary and not
    #: the parsed rows: a tax authority's report runs to thousands of them, and
    #: the rows already reach reconciliation straight from the file. What a
    #: reviewer needs here is enough to tell that the right file was read.
    summary: dict[str, Any]
    #: The periods the file covers, as `YYYY`/`YYYY-MM` keys. Plain strings
    #: because the document context has no period type of its own — what it
    #: does with them is hand them to whoever does.
    periods: tuple[str, ...] = ()


class SourceNotParsable(Exception):
    """The bytes are not the format the chosen source parses."""


class DocumentSourceParsers(Protocol):
    """Port to whatever knows how to read a document without an AI."""

    def available(self) -> tuple[ParsableSource, ...]: ...

    def parse(self, content: DocumentContent, source_id: str) -> ParsedSource:
        """Reads `content` as `source_id`, or raises `SourceNotParsable`."""
        ...
