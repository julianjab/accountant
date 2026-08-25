"""Folding a wording down to something two documents can be compared on.

The same concept reaches us written differently by every party that prints it:
accents present or dropped, capitalised or not, padded with double spaces. Any
comparison on raw text therefore answers "different" for wordings a reader
would call identical, which is why both sides of the reconciliation fold before
they compare — the exogena's own row wordings, and the row wordings a
certificate prints beside its figures.

It lives in `core` because it is not one kind's rule: it is what "the same
words" means here.
"""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")


def fold(text: str | None) -> str:
    """Lowercase, unaccent and collapse the spacing of a wording."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _WHITESPACE.sub(" ", stripped).strip().lower()
