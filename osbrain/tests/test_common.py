"""
Test file for common module.
"""
import pytest

from osbrain.common import LogLevel


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
