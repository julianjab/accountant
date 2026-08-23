"""Account identity, which is the part of reconciliation most likely to be
wrong in a way nobody notices."""

from __future__ import annotations

import pytest

from server.shared import AccountRef, MatchStrength


def _match(left: str, right: str) -> MatchStrength:
    return AccountRef(left).match(AccountRef(right))


def test_identical_digits_match_exactly():
    assert _match("64729058562", "64729058562") is MatchStrength.EXACT
    assert _match("0064729058562", "64.729.058.562") is MatchStrength.STRONG


def test_a_truncated_disclosure_matches_the_full_number():
    assert _match("64729058562", "729058562") is MatchStrength.STRONG


def test_a_collapsed_run_of_interior_zeros_matches_only_weakly():
    """The real Bancolombia case: `0006` `000` `302947` against `0006` `302947`.

    Neither leading-zero stripping nor a suffix reconciles these, so it rates
    WEAK — the engine may act on it only with corroborating amounts.
    """
    assert _match("0006302947", "0006000302947") is MatchStrength.WEAK


def test_a_card_mask_matches_only_weakly():
    assert _match("9383", "4509129383") is MatchStrength.WEAK


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("64729058562", "87041292758"),
        # Four shared trailing digits are not evidence when neither side is a
        # mask; two unrelated long accounts collide there routinely.
        ("64729053383", "87041299383"),
        ("12345", "54321"),
    ],
)
def test_different_accounts_do_not_match(left, right):
    assert _match(left, right) is MatchStrength.NONE


def test_short_numbers_are_never_joined_by_the_lossy_normalizations():
    """Below the entropy floor, zero-collapsing would merge real accounts."""
    assert _match("1002", "12") is MatchStrength.NONE


def test_matching_is_symmetric():
    for left, right in (("0006302947", "0006000302947"), ("64729058562", "729058562")):
        assert _match(left, right) is _match(right, left)
