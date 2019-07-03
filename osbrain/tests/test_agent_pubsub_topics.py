import pytest

from osbrain import run_agent
from osbrain.address import AgentAddressSerializer
from osbrain.helper import last_received_endswith
from osbrain.helper import wait_agent_condition

from .common import append_received


@pytest.mark.parametrize(
    'serializer',
    AgentAddressSerializer.SERIALIZER_SEPARATOR
)
def test_pubsub_topics_separator(nsproxy, serializer):
    """
    Simple publisher-subscriber pattern test using serializers that
    require a separation in message composition.

    Different messages sent with different agents subscribed to different
    topics are tested within this method.
    """
    a0 = run_agent('a0')
    a1 = run_agent('a1')
    a2 = run_agent('a2')
    a3 = run_agent('a3')
    a4 = run_agent('a4')
    a5 = run_agent('a5')

    for agent in (a1, a2, a3, a4, a5):
        agent.set_attr(received=[])

    addr = a0.bind('PUB', alias='pub', serializer=serializer)

    a1.connect(addr, handler=append_received)
    a2.connect(addr, handler={'foo': append_received})
    a3.connect(addr, handler={'bar': append_received,
                              'foo': append_received})
    a4.connect(addr, handler={'bar': append_received})
    a5.connect(addr, handler={'fo': append_received})

    # Make sure all agents are connected
    a0.each(0.1, 'send', 'pub', 'first', topic='foo')
    a0.each(0.1, 'send', 'pub', 'first', topic='bar')
    for agent in (a1, a2, a3, a4, a5):
        assert wait_agent_condition(agent, last_received_endswith, 'first')
    a0.stop_all_timers()

    # Send some messages
    message_01 = 'Hello'
    a0.send('pub', message_01)

    message_02 = 'World'
    a0.send('pub', message_02, topic='foo')

    message_03 = 'FOO'
    a0.send('pub', message_03, topic='foobar')

    message_04 = 'BAR'
    a0.send('pub', message_04, topic='fo')

    # Make sure all messages are processed
    a0.send('pub', 'last', topic='foo')
    a0.send('pub', 'last', topic='bar')
    for agent in (a1, a2, a3, a4, a5):
        assert wait_agent_condition(agent, last_received_endswith, 'last')

    # Check each agent received the corresponding messages
    assert message_01 in a1.get_attr('received')
    assert message_02 in a1.get_attr('received')
    assert message_03 in a1.get_attr('received')
    assert message_04 in a1.get_attr('received')

    assert message_01 not in a2.get_attr('received')
    assert message_02 in a2.get_attr('received')
    assert message_03 in a2.get_attr('received')
    assert message_04 not in a2.get_attr('received')

    assert message_01 not in a3.get_attr('received')
    assert message_02 in a3.get_attr('received')
    assert message_03 in a3.get_attr('received')
    assert message_04 not in a3.get_attr('received')

    assert message_01 not in a4.get_attr('received')
    assert message_02 not in a4.get_attr('received')
    assert message_03 not in a4.get_attr('received')
    assert message_04 not in a4.get_attr('received')

    assert message_01 not in a5.get_attr('received')
    assert message_02 in a5.get_attr('received')
    assert message_03 in a5.get_attr('received')
    assert message_04 in a5.get_attr('received')


@pytest.mark.parametrize(
    'serializer',
    AgentAddressSerializer.SERIALIZER_SIMPLE
)
def test_pubsub_topics_raw(nsproxy, serializer):
    """
    Simple publisher-subscriber pattern test.

    Different messages sent with different agents subscribed to different
    topics are tested within this method.

    In the raw version of PUBSUB, we want to replicate the raw message passing
    of ZMQ, in which the topic is passed along the message and it is the
    responsibility of the handler to split them.
    """
    a0 = run_agent('a0')
    a1 = run_agent('a1')
    a2 = run_agent('a2')
    a3 = run_agent('a3')
    a4 = run_agent('a4')
    a5 = run_agent('a5')

    for agent in (a1, a2, a3, a4, a5):
        agent.set_attr(received=[])

    addr = a0.bind('PUB', alias='pub', serializer=serializer)

    a1.connect(addr, handler=append_received)
    a2.connect(addr, handler={'foo': append_received})
    a3.connect(addr, handler={'bar': append_received,
                              'foo': append_received})
    a4.connect(addr, handler={'bar': append_received})
    a5.connect(addr, handler={'fo': append_received})

    # Make sure all agents are connected
    a0.each(0.1, 'send', 'pub', b'first', topic='foo')
    a0.each(0.1, 'send', 'pub', b'first', topic='bar')
    for agent in (a1, a2, a3, a4, a5):
        assert wait_agent_condition(agent, last_received_endswith, b'first')
    a0.stop_all_timers()

    # Send some messages
    message_01 = b'Hello'
    a0.send('pub', message_01)

    message_02 = b'World'
    a0.send('pub', message_02, topic='foo')

    message_03 = b'FOO'
    a0.send('pub', message_03, topic='foobar')

    message_04 = b'BAR'
    a0.send('pub', message_04, topic='fo')

    # Make sure all agents are connected
    a0.send('pub', b'last', topic='foo')
    a0.send('pub', b'last', topic='bar')
    for agent in (a1, a2, a3, a4, a5):
        assert wait_agent_condition(agent, last_received_endswith, b'last')

    # Check each agent received the corresponding messages
    assert message_01 in a1.get_attr('received')
    assert b'fooWorld' in a1.get_attr('received')
    assert b'foobarFOO' in a1.get_attr('received')
    assert b'foBAR' in a1.get_attr('received')

    assert message_01 not in a2.get_attr('received')
    assert b'fooWorld' in a2.get_attr('received')
    assert b'foobarFOO' in a2.get_attr('received')
    assert b'foBAR' not in a2.get_attr('received')

    assert message_01 not in a3.get_attr('received')
    assert b'fooWorld' in a3.get_attr('received')
    assert b'foobarFOO' in a3.get_attr('received')
    assert b'foBAR' not in a3.get_attr('received')

    assert message_01 not in a4.get_attr('received')
    assert b'fooWorld' not in a4.get_attr('received')
    assert b'foobarFOO' not in a4.get_attr('received')
    assert b'foBAR' not in a4.get_attr('received')

    assert message_01 not in a5.get_attr('received')
    assert b'fooWorld' in a5.get_attr('received')
    assert b'foobarFOO' in a5.get_attr('received')
    assert b'foBAR' in a5.get_attr('received')
