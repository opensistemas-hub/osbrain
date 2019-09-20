import sys

from pytest import mark

skip_windows = mark.skipif(
    sys.platform == 'win32', reason='Not supported on windows'
)
skip_windows_port_reuse = mark.skipif(
    sys.platform == 'win32', reason='Windows allows port reuse'
)
skip_windows_any_port = mark.skipif(
    sys.platform == 'win32',
    reason='Windows allows binding to well-known ports',
)
skip_windows_spawn = mark.skipif(
    sys.platform == 'win32', reason='Windows does not support fork'
)
skip_windows_ipc = mark.skipif(
    sys.platform == 'win32', reason='Windows does not support IPC'
)


def append_received(agent, message, topic=None):
    agent.received.append(message)


def set_received(agent, message, topic=None):
    agent.received = message


def echo_handler(agent, message):
    return message
