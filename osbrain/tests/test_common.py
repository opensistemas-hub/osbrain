"""
Test file for common module.
"""
import pytest

from osbrain.agent import TOPIC_SEPARATOR
from osbrain.common import unique_identifier
from osbrain.common import LogLevel


def test_unique_identifier():
    """
    The `unique_identifier` function must return an identifier that does not
    contain the `osbrain.TOPIC_SEPARATOR`, so that it is safe to use in
    PUB-SUB communication patterns.
    """
    for i in range(1000):
        identifier = unique_identifier()
        assert isinstance(identifier, bytes)
        assert TOPIC_SEPARATOR not in identifier


def test_loglevel():
    """
    Test LogLevel class initialization.
    """
    # Valid initialization
    for level in ['ERROR', 'WARNING', 'INFO', 'DEBUG']:
        LogLevel(level)
    # Invalid initialization
    with pytest.raises(ValueError):
        LogLevel('FOO')
