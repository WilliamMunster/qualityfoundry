"""Sample test file with failures for run_pytest tool testing.

This file is used as a fixture for testing the run_pytest tool's
failure handling. It should not be run as part of the main test suite.
"""


def test_passing():
    """A passing test."""
    assert True


def test_failing():
    """A failing test."""
    assert 1 == 2, "This test is designed to fail"


def test_also_passing():
    """Another passing test."""
    assert 42 == 42
