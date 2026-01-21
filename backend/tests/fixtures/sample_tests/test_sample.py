"""Sample test file for run_pytest tool testing.

This file is used as a fixture for testing the run_pytest tool.
It should not be run as part of the main test suite.
"""


def test_passing():
    """A simple passing test."""
    assert 1 + 1 == 2


def test_another_passing():
    """Another passing test."""
    assert "hello".upper() == "HELLO"


class TestSampleClass:
    """A sample test class."""

    def test_method_one(self):
        assert [1, 2, 3][0] == 1

    def test_method_two(self):
        assert {"key": "value"}["key"] == "value"
