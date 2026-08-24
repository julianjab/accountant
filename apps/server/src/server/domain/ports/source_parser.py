from dataclasses import dataclass
from typing import Any, Protocol

from server.domain.ports.document_storage import DocumentContent


@dataclass(frozen=True, slots=True)
class ParsedSource:
    """What a dedicated parser made of a file.

    Some documents are not extracted against a configured document type at
    all: a tax authority's generated spreadsheet has an exact parser instead,
    because running a language model over a thousand-row financial table costs
    money per run, varies between runs, and can misread a digit the whole
    report then rests on.
    """

    source_id: str
    #: What was read, summarised for display. Deliberately a summary and not
    #: the parsed rows: the report runs to thousands of them, and the rows
    #: already reach reconciliation straight from the file. What a reviewer
    #: needs here is enough to tell that the right file was read.
    summary: dict[str, Any]
    #: The periods the file covers, as `YYYY`/`YYYY-MM` keys. Plain strings
    #: because the document context has no period type of its own — what it
    #: does with them is hand them to whoever does.
    periods: tuple[str, ...] = ()


class DocumentSourceParsers(Protocol):
    """Port to whatever knows how to read a document without an AI."""

    def handles(self, mime_type: str) -> bool:
        """Whether any parser could read a file of this type.

        Asked before the bytes are fetched, so the ordinary case — a PDF
        certificate, which no parser handles — never pays for a download it
        does not need.
        """
        ...

    def recognize(self, content: DocumentContent) -> ParsedSource | None:
        """Reads the file with whichever parser claims it, or None.

        None is an ordinary answer, not a failure: a client's folder holds all
        sorts of spreadsheets and most of them are nobody's report. The caller
        falls back to OCR against the configured document types.
        """
        ...
