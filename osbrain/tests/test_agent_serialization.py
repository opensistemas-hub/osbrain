import time
import pickle
import json

import zmq
import pytest

import osbrain
from osbrain import run_agent
from osbrain.agent import serialize_message
from osbrain.agent import deserialize_message
from osbrain.agent import compose_message
from osbrain.agent import TOPIC_SEPARATOR
from osbrain.address import AgentAddressSerializer

from common import nsproxy  # pragma: no flakes


def set_received(agent, message, topic=None):
    agent.received = message


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


def test_reqrep_raw(nsproxy):
    """
    Simple request-reply pattern between two agents with raw serialization.
    """
    def rep_handler(agent, message):
        return b'OK'

    a0 = run_agent('a0')
    a1 = run_agent('a1')
    addr = a0.bind('REP', 'reply', rep_handler, serializer='raw')
    a1.connect(addr, 'request')
    response = a1.send_recv('request', b'Hello world')
    assert response == b'OK'


def test_reqrep_pickle(nsproxy):
    """
    Simple request-reply pattern between two agents with pickle serialization.
    """
    def rep_handler(agent, message):
        return 'OK'

    a0 = run_agent('a0')
    a1 = run_agent('a1')
    addr = a0.bind('REP', 'reply', rep_handler, serializer='pickle')
    a1.connect(addr, 'request')
    response = a1.send_recv('request', 'Hello world')
    assert response == 'OK'


def test_reqrep_json(nsproxy):
    """
    Simple request-reply pattern between two agents with json serialization.
    """
    def rep_handler(agent, message):
        return 'OK'

    a0 = run_agent('a0')
    a1 = run_agent('a1')
    addr = a0.bind('REP', 'reply', rep_handler, serializer='json')
    a1.connect(addr, 'request')
    response = a1.send_recv('request', 'Hello world')
    assert response == 'OK'


def test_reqrep_raw_zmq_outside(nsproxy):
    """
    Simple request-reply pattern between an agent and a direct ZMQ connection.
    """
    def rep_handler(agent, message):
        return message

    # Create an osBrain agent that will receive the message
    a1 = run_agent('a1')
    a1.set_attr(received=None)
    addr = a1.bind('REP', transport='tcp', handler=rep_handler,
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


def test_pushpull_raw(nsproxy):
    """
    Simple push-pull pattern test, using raw serialization between agents.
    """
    a0 = run_agent('a0')
    a1 = run_agent('a1')
    a1.set_attr(received=None)
    addr = a1.bind('PULL', handler=set_received, serializer='raw')
    a0.connect(addr, 'push')
    message = b'Hello world'
    a0.send('push', message)
    while not a1.get_attr('received'):
        time.sleep(0.01)
    assert a1.get_attr('received') == message


def test_pushpull_pickle(nsproxy):
    """
    Simple push-pull pattern test with pickle serialization.
    """
    a0 = run_agent('a0')
    a1 = run_agent('a1')
    a1.set_attr(received=None)
    addr = a1.bind('PULL', handler=set_received, serializer='pickle')
    a0.connect(addr, 'push')
    message = 'Hello world'
    a0.send('push', message)
    while not a1.get_attr('received'):
        time.sleep(0.01)
    assert a1.get_attr('received') == message


def test_pushpull_json(nsproxy):
    """
    Simple push-pull pattern test with json serialization.
    """
    a0 = run_agent('a0')
    a1 = run_agent('a1')
    a1.set_attr(received=None)
    addr = a1.bind('PULL', handler=set_received, serializer='json')
    a0.connect(addr, 'push')
    message = 'Hello world'
    a0.send('push', message)
    while not a1.get_attr('received'):
        time.sleep(0.01)
    assert a1.get_attr('received') == message


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
    while not a1.get_attr('received'):
        time.sleep(0.01)
    assert a1.get_attr('received') == message

    socket.close()
    context.destroy()


def test_pubsub_raw(nsproxy):
    """
    Simple publisher-subscriber pattern test.
    """
    a0 = run_agent('a0')
    a1 = run_agent('a1')
    a1.set_attr(received=None)
    addr = a0.bind('PUB', alias='pub', serializer='raw')
    a1.connect(addr, handler=set_received)
    message = b'Hello world'
    while not a1.get_attr('received'):
        a0.send('pub', message)
        time.sleep(0.1)
    assert a1.get_attr('received') == message


def test_pubsub_pickle(nsproxy):
    """
    Simple publisher-subscriber pattern test with pickle serialization.
    """
    a0 = run_agent('a0')
    a1 = run_agent('a1')
    a1.set_attr(received=None)
    addr = a0.bind('PUB', alias='pub', serializer='pickle')
    a1.connect(addr, handler=set_received)
    message = 'Hello world'
    while not a1.get_attr('received'):
        a0.send('pub', message)
        time.sleep(0.1)
    assert a1.get_attr('received') == message


def test_pubsub_json(nsproxy):
    """
    Simple publisher-subscriber pattern test with json serialization.
    """
    a0 = run_agent('a0')
    a1 = run_agent('a1')
    a1.set_attr(received=None)
    addr = a0.bind('PUB', alias='pub', serializer='json')
    a1.connect(addr, handler=set_received)
    message = 'Hello world'
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
