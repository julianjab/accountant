from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ContributionStatus(StrEnum):
    """What a document ended up contributing to a reconciliation, and why.

    A document can be PROCESSED, show its extracted fields, and still feed the
    reconciliation nothing at all — because its type was never mapped, because
    the mapping points at a field that is not an identifier, because the
    certificate covers another year. Those all looked identical from outside:
    a green badge and a claim reported as missing, with no way to connect the
    two. This is the connection.
    """

    #: Facts reached the engine.
    CONTRIBUTED = "contributed"
    #: The kind parsed this itself — the exogena report.
    SPINE_PARSED = "spine_parsed"
    #: Intake has not finished with it, or gave up on it.
    NOT_READY = "not_ready"
    #: Classified, but its type has no concept mapping for this kind.
    TYPE_NOT_MAPPED = "type_not_mapped"
    #: Never classified, so there is no type whose mapping could apply.
    NOT_CLASSIFIED = "not_classified"
    #: Processed but no extracted fields were stored.
    NO_EXTRACTION = "no_extraction"
    #: The mapping could not say who reports these amounts, so every fact was
    #: discarded — a fact that cannot be attributed backs nobody's claim.
    NO_REPORTING_PARTY = "no_reporting_party"
    #: Facts were produced, but for a different period than the one requested.
    OTHER_PERIOD = "other_period"
    #: Mapped and extracted, yet no mapped field held a readable amount.
    NO_AMOUNTS = "no_amounts"
    #: Its bytes could not be read.
    UNREADABLE = "unreadable"

    @property
    def is_useful(self) -> bool:
        return self in (ContributionStatus.CONTRIBUTED, ContributionStatus.SPINE_PARSED)


@dataclass(frozen=True, slots=True)
class DocumentContribution:
    """One document's part in a reconciliation run."""

    document_id: str
    file_name: str
    status: ContributionStatus
    fact_count: int = 0
    #: Free text naming the specific cause — the field that was not an
    #: identifier, the period the document actually covers.
    detail: str = ""


@dataclass(frozen=True, slots=True)
class GatheredFacts:
    """Everything a reconciliation run needs, plus what each document did.

    The contributions travel with the facts rather than being recomputed
    later: only the gathering knows why a document yielded nothing, and by the
    time the engine sees a bare list of facts that reason is gone.
    """

    facts: tuple
    contributions: tuple[DocumentContribution, ...] = ()
