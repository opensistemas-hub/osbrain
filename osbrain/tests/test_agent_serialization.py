import json
import pickle
import time

import pytest
import zmq

import osbrain
from osbrain import run_agent
from osbrain.address import AgentAddressSerializer
from osbrain.agent import TOPIC_SEPARATOR
from osbrain.agent import compose_message
from osbrain.agent import deserialize_message
from osbrain.agent import serialize_message
from osbrain.helper import wait_agent_attr

from .common import echo_handler
from .common import set_received


def test_compose_message():
    """
    Test correct message composing.
    """
    message = b'message'
    topic = b'test topic'

    # Basic composing
    for serializer in AgentAddressSerializer.SERIALIZER_SIMPLE:
        serializer = AgentAddressSerializer(serializer)
        assert compose_message(message, topic, serializer) \
            == topic + message
    for serializer in AgentAddressSerializer.SERIALIZER_SEPARATOR:
        serializer = AgentAddressSerializer(serializer)
        assert compose_message(message, topic, serializer) \
            == topic + TOPIC_SEPARATOR + message

    # Raise with wrong serializer
    with pytest.raises(Exception):
        compose_message(message, topic, 'foo')


@pytest.mark.parametrize('agent_serial,socket_serial,result', [
    (None, None, osbrain.config['SERIALIZER']),
    ('raw', None, 'raw'),
    ('pickle', None, 'pickle'),
    (None, 'raw', 'raw'),
    (None, 'json', 'json'),
    ('pickle', 'json', 'json'),
])
def test_correct_serialization(nsproxy, agent_serial, socket_serial, result):
    """
    Test that the right serializer is being used when using the different
    initialization options.
    """
    agent = run_agent('a0', serializer=agent_serial)
    addr = agent.bind('PUB', serializer=socket_serial)
    assert addr.serializer == result


def test_serialize_message():
    """
    Test basic serialization.
    """
    # Raw serialization
    test = b'asdf'
    message = serialize_message(message=test, serializer='raw')
    assert isinstance(message, bytes)
    assert test == message

    # Pickle serialization
    test = [0, 1]
    message = serialize_message(message=test, serializer='pickle')
    assert isinstance(message, bytes)
    assert test == pickle.loads(message)

    # Json serialization
    test = [0, 1]
    message = serialize_message(message=test, serializer='json')
    assert isinstance(message, bytes)
    assert test == json.loads(message.decode('ascii'))

    # Un-serializable type
    with pytest.raises(TypeError):
        serialize_message(message=b'Hello', serializer='json')

    # Incorrect serializer
    with pytest.raises(ValueError):
        serialize_message(message=test, serializer='foo')


def test_deserialize_message():
    """
    Test basic deserialization.
    """
    # Raw deserialization
    test = b'asdf'
    assert test == deserialize_message(message=test, serializer='raw')

    # Pickle deserialization
    test = [0, 1]
    assert test == deserialize_message(message=pickle.dumps(test, -1),
                                       serializer='pickle')

    # Json deserialization
    assert test == \
        deserialize_message(message=json.dumps(test).encode('ascii'),
                            serializer='json')

    # Incorrect serializer
    with pytest.raises(ValueError):
        deserialize_message(message=b'x', serializer='foo')


@pytest.mark.parametrize('serializer, message, response', [
    ('raw', b'Hello world', b'OK'),
    ('pickle', 'Hello world', 'OK'),
    ('json', 'Hello world', 'OK'),
])
def test_reqrep(nsproxy, serializer, message, response):
    """
    Simple request-reply pattern between two agents with different
    serializations.
    """
    def rep_handler(agent, message):
        return response

    a0 = run_agent('a0')
    a1 = run_agent('a1')
    addr = a0.bind('REP', 'reply', rep_handler, serializer=serializer)
    a1.connect(addr, 'request')
    assert a1.send_recv('request', message) == response


def test_reqrep_raw_zmq_outside(nsproxy):
    """
    Simple request-reply pattern between an agent and a direct ZMQ connection.
    """
    # Create an osBrain agent that will receive the message
    a1 = run_agent('a1')
    a1.set_attr(received=None)
    addr = a1.bind('REP', transport='tcp', handler=echo_handler,
                   serializer='raw')

    # Create a raw ZeroMQ REQ socket
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect('tcp://%s:%s' % (addr.address.host, addr.address.port))

    # Send the message
    message = b'Hello world'
    socket.send(message)
    assert socket.recv() == message

    socket.close()
    context.destroy()


@pytest.mark.parametrize('serializer, message', [
    ('raw', b'Hello world'),
    ('pickle', 'Hello world'),
    ('json', 'Hello world'),
])
def test_pushpull(nsproxy, serializer, message):
    """
    Simple push-pull pattern test, using different serializations.
    """
    a0 = run_agent('a0')
    a1 = run_agent('a1')
    a1.set_attr(received=None)
    addr = a1.bind('PULL', handler=set_received, serializer=serializer)
    a0.connect(addr, 'push')
    a0.send('push', message)
    assert wait_agent_attr(a1, name='received', value=message)


def test_pushpull_raw_zmq_outside(nsproxy):
    """
    Simple push-pull pattern test. Channel without serialization.

    The message is sent from outside osBrain, through a ZMQ PUSH socket.
    """
    # Create an osBrain agent that will receive the message
    a1 = run_agent('a1')
    a1.set_attr(received=None)
    addr = a1.bind('PULL', transport='tcp', handler=set_received,
                   serializer='raw')

    # Create a raw ZeroMQ PUSH socket
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    socket.connect('tcp://%s:%s' % (addr.address.host, addr.address.port))

    # Send the message
    message = b'Hello world'
    socket.send(message)
    assert wait_agent_attr(a1, name='received', value=message)

    socket.close()
    context.destroy()


@pytest.mark.parametrize('serializer, message', [
    ('raw', b'Hello world'),
    ('pickle', 'Hello world'),
    ('json', 'Hello world'),
])
def test_pubsub(nsproxy, serializer, message):
    """
    Simple publisher-subscriber pattern test with different serializations.
    """
    a0 = run_agent('a0')
    a1 = run_agent('a1')
    a1.set_attr(received=None)
    addr = a0.bind('PUB', alias='pub', serializer=serializer)
    a1.connect(addr, handler=set_received)
    while not a1.get_attr('received'):
        a0.send('pub', message)
        time.sleep(0.1)
    assert a1.get_attr('received') == message


def test_pubsub_raw_zmq_outside(nsproxy):
    """
    Simple publisher-subscriber pattern test. Channel without serialization.

    The message is sent from outside osBrain, through a ZMQ PUB socket.
    """
    # Create an osBrain agent that will receive the message
    a1 = run_agent('a1')
    a1.set_attr(received=None)
    addr = a1.bind('SUB', transport='tcp', handler=set_received,
                   serializer='raw')

    # Create a raw ZeroMQ PUB socket
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.connect('tcp://%s:%s' % (addr.address.host, addr.address.port))

    # Send the message
    message = b'Hello world'
    while not a1.get_attr('received'):
        socket.send(message)
        time.sleep(0.01)
    assert a1.get_attr('received') == message

    socket.close()
    context.destroy()
