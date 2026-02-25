"""Example test file — delete or replace with real tests."""

import pytest


def test_addition():
    assert 1 + 1 == 2


def test_string_contains():
    assert "hello" in "hello world"


@pytest.mark.parametrize(
    "value, expected",
    [
        (0, True),
        (2, True),
        (3, False),
        (4, True),
    ],
)
def test_is_even(value, expected):
    assert (value % 2 == 0) == expected
