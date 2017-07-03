"""
Test file for common module.
"""
import pytest

from osbrain.agent import TOPIC_SEPARATOR
from osbrain.common import unique_identifier
from osbrain.common import LogLevel
from osbrain.common import topic_to_bytes
from osbrain.common import topics_to_bytes


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


def test_topic_to_bytes():
    """
    Test the topic to bytes function.
    """
    assert topic_to_bytes('foo') == b'foo'
    assert topic_to_bytes(b'bar') == b'bar'


def test_topics_to_bytes_without_uuid():
    """
    Test topics_to_bytes basic usage, without specifying a uuid.
    """
    handlers = {'topic_one': 'handler', b'topic_two': 'handler'}

    curated = topics_to_bytes(handlers)
    assert isinstance(curated, dict)

    for k, v in curated.items():
        assert isinstance(k, bytes)
        assert k.startswith(b'topic_')
        assert v == 'handler'


@pytest.mark.parametrize('uuid', [b'', b'U'])
def test_topics_to_bytes_with_uuid(uuid):
    """
    Test topics_to_bytes basic usage, specifying different uuid's.
    """
    handlers = {'topic_one': 'handler', b'topic_two': 'handler'}

    curated = topics_to_bytes(handlers, uuid=uuid)
    assert isinstance(curated, dict)

    for k, v in curated.items():
        assert isinstance(k, bytes)
        assert k.startswith(uuid + b'topic_')
        assert v == 'handler'
