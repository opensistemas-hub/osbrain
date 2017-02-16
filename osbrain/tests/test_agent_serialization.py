import time
import pickle
import json

import zmq
import pytest

from osbrain import run_agent
from osbrain.agent import serialize_message
from osbrain.agent import deserialize_message
from osbrain.agent import compose_message

from common import nsaddr  # pragma: no flakes
from common import nsproxy  # pragma: no flakes


def set_received(agent, message, topic=None):
    agent.received = message


def test_message_composer():
    msg_1 = b'Chain of bytes'
    msg_2 = [1, 3, "Hello"]
    topic = "test topic"
    topic_bytes = b"test topic"

    separator = b'\x80'

    # Test raw serialization composing
    assert compose_message('raw', msg_1) == b'Chain of bytes'
    assert compose_message('raw', msg_1, topic) == b'test topicChain of bytes'

    # Test pickle serialization composing
    assert compose_message('pickle', msg_1) == pickle.dumps(msg_1, -1)
    assert compose_message('pickle', msg_2) == pickle.dumps(msg_2, -1)

    assert compose_message('pickle', msg_1, topic) \
        == topic_bytes + separator + pickle.dumps(msg_1, -1)
    assert compose_message('pickle', msg_2, topic) \
        == topic_bytes + separator + pickle.dumps(msg_2, -1)

    # Test json serialization composing
    msg_1_str = 'Chain of bytes'

    assert compose_message('json', msg_1_str) \
        == json.dumps(msg_1_str).encode('ascii')
    assert compose_message('json', msg_2) \
        == json.dumps(msg_2).encode('ascii')

    assert compose_message('json', msg_1_str, topic) \
        == topic_bytes + separator + json.dumps(msg_1_str).encode('ascii')
    assert compose_message('json', msg_2, topic) \
        == topic_bytes + separator + json.dumps(msg_2).encode('ascii')


def test_serialize_message():
    """
    Test basic serialization.
    """
    test = b'asdf'
    assert test == serialize_message(message=test, serializer='raw')
    test = [0, 1]
    assert test == pickle.loads(serialize_message(message=test,
                                serializer='pickle'))
    assert test == json.loads(serialize_message(message=test,
                              serializer='json').decode('ascii'))
    with pytest.raises(ValueError):
        serialize_message(message=test, serializer='foo')


def test_deserialize_message():
    """
    Test basic deserialization.
    """
    test = b'asdf'
    assert test == deserialize_message(message=test, serializer='raw')
    test = [0, 1]
    assert test == deserialize_message(message=pickle.dumps(test, -1),
                                       serializer='pickle')
    assert test == deserialize_message(message=json.dumps(test).encode('ascii'),
                                       serializer='json')
    with pytest.raises(ValueError):
        deserialize_message(message=b'x', serializer='foo')


def test_reqrep_raw(nsaddr):
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


def test_reqrep_pickle(nsaddr):
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


def test_reqrep_json(nsaddr):
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


def test_reqrep_raw_zmq_outside(nsaddr):
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


def test_pushpull_raw(nsaddr):
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


def test_pushpull_pickle(nsaddr):
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


def test_pushpull_json(nsaddr):
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


def test_pushpull_raw_zmq_outside(nsaddr):
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


def test_pubsub_raw(nsaddr):
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


def test_pubsub_pickle(nsaddr):
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


def test_pubsub_json(nsaddr):
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


def test_pubsub_raw_zmq_outside(nsaddr):
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
