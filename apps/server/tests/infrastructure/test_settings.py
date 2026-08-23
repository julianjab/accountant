"""The allowlist is the only thing standing between the API and any Google account."""

import pytest

from server.infrastructure.config.settings import Settings


def settings(allowed: str) -> Settings:
    return Settings(allowed_sign_ins=allowed)


def test_an_empty_allowlist_admits_nobody():
    # The default must fail closed: a misconfigured deploy locks everyone out
    # rather than exposing the clients' tax data.
    assert not settings("").allows("a@b.com")


@pytest.mark.parametrize(
    ("allowed", "email", "expected"),
    [
        ("a@b.com", "a@b.com", True),
        ("a@b.com", "other@b.com", False),
        ("@lahaus.com", "julian@lahaus.com", True),
        ("@lahaus.com", "julian@gmail.com", False),
        ("a@b.com, @lahaus.com", "julian@lahaus.com", True),
        ("a@b.com, @lahaus.com", "a@b.com", True),
        ("a@b.com, @lahaus.com", "z@z.com", False),
    ],
)
def test_entries_match_exact_emails_and_domains(allowed, email, expected):
    assert settings(allowed).allows(email) is expected


def test_matching_ignores_case_and_surrounding_space():
    assert settings("  A@B.com ").allows("a@b.COM")


@pytest.mark.parametrize(
    "email",
    ["julian@notlahaus.com", "julian@evil-lahaus.com", "lahaus.com@evil.com"],
)
def test_a_domain_entry_does_not_admit_a_lookalike(email):
    # The "@" must be part of the match, or any domain ending in the same text
    # would get in.
    assert not settings("@lahaus.com").allows(email)
