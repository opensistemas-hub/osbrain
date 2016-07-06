import zmq
from osbrain.address import AgentAddressKind
from osbrain.address import AgentAddressRole


def twin_list(elements):
    result = elements[:]
    result[1::2] = elements[::2]
    result[::2] = elements[1::2]
    return result


def test_kind():
    """
    This test aims to cover basic AgentAddressKind operations: initialization,
    equivalence and basic methods.
    """
    strings = ['REQ', 'REP', 'PUSH', 'PULL', 'PUB', 'SUB']
    zmqints = [zmq.REQ, zmq.REP, zmq.PUSH, zmq.PULL, zmq.PUB, zmq.SUB]
    handlers = [False, True, False, True, False, True]
    strtwins = twin_list(strings)
    zmqtwins = twin_list(zmqints)
    configurations = zip(strings, strtwins, zmqints, zmqtwins, handlers)
    # Make sure there are no missing values
    assert len(list(configurations)) == len(strings)

    for string, strtwin, zmqint, zmqtwin, handler in configurations:
        # Initialization and equivalence
        kind = AgentAddressKind(string)
        assert kind == zmqint
        assert kind == string
        assert kind == AgentAddressKind(zmqint)
        assert kind == AgentAddressKind(kind)
        # Basic methods
        assert isinstance(kind.twin(), AgentAddressKind)
        assert kind.twin() == strtwin
        assert kind.requires_handler() == handler


def test_role():
    """
    This test aims to cover basic AgentAddressRole operations: initialization,
    equivalence and basic methods.
    """
    values = ['server', 'client']
    twins = twin_list(values)
    for value, twin in zip(values, twins):
        # Initialization and equivalence
        role = AgentAddressRole(value)
        assert role == value
        assert role == AgentAddressRole(role)
        # Basic methods
        assert isinstance(role.twin(), AgentAddressRole)
        assert role.twin() == twin
