"""
Core agent classes.
"""
import zmq
import signal
import sys
import multiprocessing
import pprint
import pickle
import errno

from multiprocessing.queues import Queue

from .message import Message
from .message import Types as mType


# TODO:
#   - Consider removing message types?
#       - Perhaps it is fine as long as they are all hidden from the user.
#         (only for basic, low-level messages types!)
#       - Or even better, create a list of "commands" i.e. !PING, !DIE, ...
#         which can be used by the user (create tests for each command).
#   - Message should be hidden from the user: i.e. allow the user to pass
#     messages with 2 parameters (that will automatically be wrapped in a
#     message?
#   - Do not require a message to inherit from Message (it could be anything)?
#       - Perhaps it is fine if we allow a string as Message type (then only
#         the type would be required.
#       - Implement __eq__ to compare a Message to its topic.
#       - Reconsider attribute name `type` to: topic? header? key?...
#   - Tests, tests, tests!
#   - Rethink Agent class and methods (better API)
#   - Implement logging mechanisms (deprecate info(), warn(), ...)
#   - Automatically handle error replies (i.e. log error and skip processing?)
#   - An Agent should only have a REP socket at first. Then any number and
#     type of sockets could be added to it.
#   - Perhaps the init_agent() method makes no sense (could be embedded in
#     __init__().


class AgentSock(object):
    """
    Agent socket information consisting on the host and port.

    Parameters
    ----------
    host : str
        Agent host.
    port : int
        Agent port.

    Attributes
    ----------
    host : str
        Agent host.
    port : int
        Agent port.
    """
    def __init__(self, host, port):
        assert isinstance(host, str), \
            'Incorrect parameter host on AgentSock; expecting type str.'
        assert isinstance(port, int), \
            'Incorrect parameter port on AgentSock; expecting type int.'
        self.host = host
        self.port = port

    def __repr__(self):
        """
        Return the string representation of the AgentSock.

        Returns
        -------
        representation : str
        """
        return '%s:%s' % (self.host, self.port)

    def __hash__(self):
        return hash(self.host) ^ hash(self.port)

    def __eq__(self, other):
        if not isinstance(other, AgentSock):
            return False
        return self.host == other.host and self.port == other.port


class AgentRPP(object):
    """
    Agent's REP-PUB-PULL socket information.

    Parameters
    ----------
    host : str
        Agent host (same for all agent's sockets).
    ports : int / list / dict
        Socket ports. An integer number will be translated to automatically
        chosen free ports. A list can be given where its elements correspond
        to the REP, PUB and PULL sockets in that order. Also, a dictionary
        can be given with 'rep', 'pub' and 'pull' as string keys for the ports.

    Attributes
    ----------
    host : str
        Agent host (same for all agent's sockets).
    port : dict
        Socket ports. A dictionary with 'rep', 'pub' and 'pull' as keys
        for storing each port number.
    """
    def __init__(self, host='127.0.0.1', ports=0):
        assert isinstance(host, str), \
            'Incorrect parameter host on AgentRPP; expecting type str.'
        assert isinstance(ports, (int, list, dict)), \
            'Incorrect ports on AgentRPP; expecting list, dict or int.'

        if isinstance(ports, int):
            ports = [0, 0, 0]
        if isinstance(ports, list):
            ports = {'rep': ports[0],
                     'pub': ports[1],
                     'pull': ports[2]}

        # Base attributes
        self.host = host
        # Make sure we always create a copy of the mutable parameters
        self.port = {'rep': ports['rep'],
                     'pub': ports['pub'],
                     'pull': ports['pull']}

    def rep(self):
        return AgentSock(self.host, self.port['rep'])

    def pub(self):
        return AgentSock(self.host, self.port['pub'])

    def pull(self):
        return AgentSock(self.host, self.port['pull'])

    def __repr__(self):
        """
        Return the string representation of the AgentSock.

        Returns
        -------
        representation : str
        """
        return '%s:%s' % (self.host, self.port)

    def __hash__(self):
        return hash(self.host) ^ \
               hash(self.port['rep']) ^ \
               hash(self.port['pub']) ^ \
               hash(self.port['pull'])

    def __eq__(self, other):
        if not isinstance(other, AgentSock):
            return False
        return self.host == other.host and self.port == other.port


class TryREP(object):
    """
    Agent class for testing purposes. It just receives requests from the
    client and is able to send back a reply.

    Parameters
    ----------
    host : string
        Agent's socket host.
    port : int
        Agent's socket port.
    """
    def __init__(self, host, port):
        self.host = host
        self.port = port
        # Socket creation
        try:
            self.ctx = zmq.Context()
            self.sck = self.ctx.socket(zmq.REP)
            if self.port == 0:
                self.port = self.sck.bind_to_random_port('tcp://%s' % host)
            else:
                self.sck.bind('tcp://%s:%s' % (self.host, self.port))
        except zmq.ZMQError as e:
            raise
        self.sock = AgentSock(self.host, self.port)

    def recv(self):
        return self.sck.recv_pyobj()

    def send(self, message):
        self.sck.send_pyobj(message)


class TryREQ(object):
    """
    Client class for testing purposes. It just connects to the agent and
    is able to send and receive messages from it.

    Parameters
    ----------
    host : string
        Agent's socket host.
    port : int
        Agent's socket port.
    """
    def __init__(self, sock):
        assert isinstance(sock, AgentSock), \
            'Wrong type for sock; expecting AgentSock.'
        self.sock = sock
        self.host = sock.host
        self.port = sock.port
        # Socket creation
        try:
            self.ctx = zmq.Context()
            self.sck = self.ctx.socket(zmq.REQ)
            self.sck.connect('tcp://%s:%s' % (self.host, self.port))
        except zmq.ZMQError as e:
            raise

    def send(self, message):
        self.sck.send_pyobj(message)

    def recv(self):
        return self.sck.recv_pyobj()

    def sendrecv(self, message):
        self.send(message)
        return self.recv()


class TryAutoRequest(multiprocessing.Process):
    def __init__(self, sock, request):
        assert isinstance(sock, AgentSock), \
            'Wrong type for sock; expecting AgentSock.'
        self.sock = sock
        self.host = sock.host
        self.port = sock.port
        # Socket creation
        try:
            self.ctx = zmq.Context()
            self.sck = self.ctx.socket(zmq.REQ)
            self.sck.connect('tcp://%s:%s' % (self.host, self.port))
        except zmq.ZMQError as e:
            raise
        self.request = request

    def run(self):
        self.sck.send_pyobj(request)
        self.sck.recv_pyobj()
        self.sck.close()


class Agent(multiprocessing.Process):
    """
    Accepts incoming requests from clients and sends a response to them.

    Parameters
    ----------
    rpp : AgentRPP, default AgentRPP()
        Agent's REP-PUB-PULL sockets information. By default, '127.0.0.1' is
        used as host and 0 is used for all ports (the OS will select random
        ports which are available).
    queue : multiprocessing.Queue, default is None
        A queue that is used to put information about the agent's socket.
        This is particularly usefull when passing 0 as port (as the agent
        will bind to a random port).

    Attributes
    ----------
    sub_sockets : list (zmq.socket(zmq.SUB))
        List containing the SUB sockets of the agent.
    sub_topics : dict
        Dictionary with SUB sockets as keys containing the list of topics
        being filtered by the SUB socket.
    sub_publishers : dict
        Dictionary with SUB sockets as keys containing the list of PUB
        agents to which the SUB socket is subscribed to.
    sub_handlers : dict
        Dictionary with SUB sockets as keys containing dictionaries with
        topics as keys containing a handler function or method to be executed
        when publication data is being processed.
    memory : dict
        Agent's memory. Any data could be stored here and would normally be
        used for synchronization between agents. When a client asks for
        synchronization with a agent, a process will begin to ensure that
        the client gets a exact copy of the agent's memory.
    poll_timeout : int
        Polling timeout in milliseconds. Set to None to set no timeout.
    """
    def __init__(self, rpp=AgentRPP(), queue=None):
        assert isinstance(rpp, AgentRPP), \
            'Incorrect parameter rpp; expecting type AgentRPP.'
        assert not queue or isinstance(queue, Queue), \
            'Incorrect parameter queue; expecting type Queue.'

        multiprocessing.Process.__init__(self)

        self.rpp = rpp
        self.queue = queue

        # TODO: self.sock and self.port should not exist anymore
        self.port = self.rpp.port['rep']
        self.sock = AgentSock(self.rpp.host, self.port)

        # Subscriptions
        self.sub_sockets = []
        self.sub_topics = {}
        self.sub_publishers = {}
        self.sub_handlers = {}

        # Agent memory
        self.memory = {}

        # Polling timeout
        self.poll_timeout = 1000

    def init_agent(self):
        """
        Initialize the agent sockets: REP, PUB and PULL.

        All the sockets get registered in the agent's poller and their
        information is transmited through the agent's queue to the parent
        process.
        """

        self.keep_alive = True

        # Socket creation
        if __debug__:
            self.info('Creating TCP socket...')
        try:
            self.ctx = zmq.Context()
            self.rep = self.ctx.socket(zmq.REP)
            self.pub = self.ctx.socket(zmq.PUB)
            self.pull = self.ctx.socket(zmq.PULL)
            # Bind REP socket
            if self.rpp.port['rep'] == 0:
                uri = 'tcp://%s' % self.rpp.host
                self.rpp.port['rep'] = self.rep.bind_to_random_port(uri)
            else:
                self.rep.bind('tcp://%s:%s' % (self.rpp.host,
                                               self.rpp.port['rep']))
            # Bind PUB socket
            if self.rpp.port['pub'] == 0:
                uri = 'tcp://%s' % self.rpp.host
                self.rpp.port['pub'] = self.pub.bind_to_random_port(uri)
            else:
                self.pub.bind('tcp://%s:%s' % (self.rpp.host,
                                               self.rpp.port['pub']))
            # Bind PULL socket
            if self.rpp.port['pull'] == 0:
                uri = 'tcp://%s' % self.rpp.host
                self.rpp.port['pull'] = self.pull.bind_to_random_port(uri)
            else:
                self.pull.bind('tcp://%s:%s' % (self.rpp.host,
                                                self.rpp.port['pull']))
        except zmq.ZMQError as e:
            self.error('Socket creation failed with: %s' % e)
            # Re-throw the exception
            raise

        try:
            self.poller = zmq.Poller()
            self.poller.register(self.rep, zmq.POLLIN)
            self.poller.register(self.pub, zmq.POLLIN)
            self.poller.register(self.pull, zmq.POLLIN)
        except:
            self.error('Error registering sockets: %s' % e)
            # Re-throw the exception
            raise

        # TODO: self.sock and self.port should not exist anymore
        self.port = self.rpp.port['rep']
        self.sock = AgentSock(self.rpp.host, self.port)

        # Put RPP information on the queue, if present
        if self.queue:
            self.queue.put(self.rpp)

    def handle_sub(self, message):
        self.warn('Method handle_sub() has not been implemented!')
        pass

    def multi_subscribe(self, publisher, handlers={}):
        """
        Subscribe to a publisher agent for multiple topics.

        A single SUB socket is created for all the subscription topics.

        Parameters
        ----------
        publisher : AgentSock
            Publisher socket.
        handlers: dict {str: function}
            Message handler functions. This functions take a parameter which
            is the message/data received from the publisher. The dictionay
            keys are the topics, for filtering.

        Returns
        -------
        zmq.sugar.socket.Socket
            The new SUB socket created.
        """
        assert isinstance(publisher, AgentSock), \
            'Wrong type for publisher; expecting AgentSock.'
        assert isinstance(handlers, dict), \
            'Wrong type for handlers; expecting dict.'

        # Default handler
        if not handlers:
            handlers[''] = self.handle_sub

        topics = [x for x in handlers]
        functs = [handlers[x] for x in handlers]

        # Create SUB socket
        sub = self.ctx.socket(zmq.SUB)
        for t in topics:
            sub.setsockopt(zmq.SUBSCRIBE, t.encode('ascii'))
        sub.connect('tcp://%s:%s' % (publisher.host, publisher.port))

        # Register SUB socket
        self.poller.register(sub, zmq.POLLIN)

        # Append socket to the list of agent SUB sockets
        self.sub_sockets.append(sub)
        # Topics for the SUB socket
        self.sub_topics[sub] = topics
        # Set SUB's topic handlers
        self.sub_handlers[sub] = handlers
        # Store SUB's publisher agent socket
        self.sub_publishers[sub] = publisher

        return sub

    def subscribe(self, publisher, topic='', handler=None):
        """
        Subscribe to a publisher agent for a single topic.

        A new SUB socket is created for the subscription.

        Parameters
        ----------
        publisher : AgentSock
            Publisher socket.
        topic : str
            Data topic, for filtering.
        handler: function/method
            Message handler function. This function takes a parameter which
            is the message/data received from the publisher.
        """
        # TODO: deprecate this function in favor of `multi_subscribe`, which
        #       should then be renamed to `subscribe`.
        assert isinstance(publisher, AgentSock), \
            'Wrong type for publisher; expecting AgentSock.'
        assert isinstance(topic, str), \
            'Wrong type for topic; expecting str.'

        # Default handler
        if not handler:
            handler = self.handle_sub

        # Create SUB socket
        sub = self.ctx.socket(zmq.SUB)
        if __debug__:
            self.info('Connecting to publisher %s with topic %s' %
                      (publisher, topic))
        sub.setsockopt(zmq.SUBSCRIBE, topic.encode('ascii'))
        sub.connect('tcp://%s:%s' % (publisher.host, publisher.port))
        # Register SUB socket
        self.poller.register(sub, zmq.POLLIN)
        if __debug__:
            self.info('Subscriber registered!')

        # Append socket to the list of agent SUB sockets
        self.sub_sockets.append(sub)
        # Update topics for the SUB socket
        if sub not in self.sub_topics:
            self.sub_topics[sub] = []
        self.sub_topics[sub].append(topic)
        # Set SUB's topic handler
        if sub not in self.sub_handlers:
            self.sub_handlers[sub] = {}
        self.sub_handlers[sub][topic] = handler
        # Store SUB's publisher agent socket
        if sub not in self.sub_publishers:
            self.sub_publishers[sub] = []
        self.sub_publishers[sub].append(publisher)

    def connect_req(self, rep):
        """
        Create a REQ socket and connect it to a given REP agent.

        Parameters
        ----------
        rep : AgentSock
            Agent's REP socket.

        Returns
        -------
        req : zmq.sugar.socket.Socket
            A REQ socket to communicate with the REP agent.
        """
        try:
            req = self.ctx.socket(zmq.REQ)
            req.connect('tcp://%s:%s' % (rep.host, rep.port))
        except zmq.ZMQError as e:
            raise
        return req

    def close_socket(self, sck):
        """
        Close a given socket.

        Parameters
        ----------
        sck : zmq.sugar.socket.Socket
            Socket to be closed.
        """
        try:
            sck.close()
        except zmq.ZMQError as e:
            raise

    def handle_private(self, request, rep):
        """
        Handle a private request received from a client.

        The request is passed as parameter to this function as well as the
        corresponding REP agent in which this request has been received.
        This function should always send back a reply to the client before
        returning.

        Parameters
        ----------
        request : Message
            Request received.
        rep : zmq.sugar.socket.Socket
            REP agent in which the request has been received.

        Returns
        -------
        bool
            False when a request for attention release is received, True
            otherwise.
        """
        if request.typ == mType.REQMEM:
            rep.send_pyobj(Message(mType.DICT, self.memory))
            return True
        if request.typ == mType.RELATT:
            rep.send_pyobj(Message(mType.OK))
            return False
        rep.send_pyobj(Message(mType.UNKNOWN))
        return True

    def wait_on(self):
        """
        Listen on a private port to the client.
        """

        try:
            rep = self.ctx.socket(zmq.REP)
            host = self.rpp.host
            port = rep.bind_to_random_port('tcp://%s' % host)
        except zmq.ZMQError as e:
            self.error('Socket creation failed with: %s' % e)
            # Re-throw the exception
            raise

        self.send_reply(Message(mType.AGENTSOCK, AgentSock(host, port)))

        keep_waiting = True

        while keep_waiting:
            try:
                request = rep.recv_pyobj()
                keep_waiting = self.handle_private(request, rep)
            except zmq.ZMQError as e:
                # Raise the exception in case it is not due to SIGINT
                if e.errno != errno.EINTR:
                    raise
                else:
                    # SIGINT should kill the agent
                    self.keep_alive = False
                    break

    def sync(self, rpp, mem_handler, handlers):
        """
        Synchronize with a given agent's memory.

        The objective is to make sure the copy we get of the agent's memory
        is an exact copy. To do so, the agent stops listening to all its
        sockets and instead starts listening to a single socket shared with
        the client. The client makes sure that is receiving messages from
        the publisher (the PUB-SUB connection is well stablished) and then
        asks for the agent's memory. Then the agent will go back to normal
        state (listening to all its sockets).

        Parameters
        ----------
        rpp : AgentRPP
            Agent's sockets information.
        mem_handler : function
            Function to be executed when the agent's memory is received.
            The data received will be passed as the only parameter of this
            function.
        handlers: dict {str: function}
            Message handler functions. This functions take a parameter which
            is the message/data received from the publisher. The dictionay
            keys are the topics, for filtering.
        """
        rep = rpp.rep()

        # Connect to REP socket
        req = self.connect_req(rep)

        # Request attention (a new socket will be created for communication)
        rep = self.request_attention(req).data

        # Subscribe
        sub = self.multi_subscribe(rpp.pub(), handlers)

        # Once we have the new REP socket, we don't need the old one
        self.close_socket(req)

        # Connect to the new REP socket
        req = self.connect_req(rep)

        # Request memory and release attention
        memory = self.request_memory(req).data
        self.release_attention(req)

        # Close the connection
        self.close_socket(req)

        # Do something with the data received from the agent
        mem_handler(memory)

    def request_attention(self, req):
        """
        Requests attention from a REP agent. This means the agent will
        stop listening on any other sockets it has and will create a new REP
        socket to listen to new requests.

        Parameters
        ----------
        req : zmq.sugar.socket.Socket
            A REQ socket connected to the REP agent.

        Returns
        -------
        new : AgentSock
            Agent's new REP socket where the agent is listening.
        """
        request = Message(mType.REQATT)
        req.send_pyobj(request)
        reply = req.recv_pyobj()
        return reply

    def request_memory(self, req):
        """
        Requests a REP agent's memory.

        Parameters
        ----------
        req : zmq.sugar.socket.Socket
            A REQ socket connected to the REP agent.
        """
        request = Message(mType.REQMEM)
        req.send_pyobj(request)
        reply = req.recv_pyobj()
        return reply

    def release_attention(self, req):
        """
        Releases attention from a REP agent. This means the agent will
        go back to normal activity, listening to all its sockets.

        Parameters
        ----------
        req : zmq.sugar.socket.Socket
            A REQ socket connected to the REP agent.
        """
        request = Message(mType.RELATT)
        req.send_pyobj(request)
        reply = req.recv_pyobj()
        return reply

    def process_publication(self, sub):
        """
        Process a new publication available in a SUB socket.

        Parameters
        ----------
        sub : SUB socket
            The SUB socket which is receiving the data.
        """
        raw = sub.recv()
        for topic in self.sub_topics[sub]:
            if topic == raw[0:len(topic)].decode('ascii'):
                data = pickle.loads(raw[len(topic):])
                self.sub_handlers[sub][topic](data)

    def publish(self, data, topic=''):
        """
        Publish some data.

        Parameters
        ----------
        data : cPickable
            Data to be published.
        topic : str
            Data topic, for subscribers filtering.
        """
        assert isinstance(topic, str), \
            'Wrong type for topic; expecting str.'
        # Publish data with pickle serialization
        self.pub.send(topic.encode('ascii') + pickle.dumps(data, -1))

    def process_request(self):
        """
        Process an incoming request: get and handle the new request.
        """
        request = self.get_request()
        reply = self.handle(request)
        if __debug__:
            if self.listening == 0:  # Check if a reply was sent to the client
                try:
                    self.send_reply(Message(mType.ERROR, 'No reply'))
                    self.warn('No reply sent back.')
                except zmq.ZMQError as e:
                    pass

    def iddle(self):
        """
        This function is to be executed when the agent is iddle.

        After a timeout occurs when the agent's poller receives no data in
        any of its sockets, the agent may execute this function.

        Note
        ----
        The timeout is set by the agent's `poll_timeout` attribute.
        """
        pass

    def loop(self):
        """
        Agent's main loop.

        This loop is executed until the `keep_alive` attribute is False
        or until an error occurs.
        """
        while self.keep_alive:
            if self.iterate():
                break

    def iterate(self):
        """
        Agent's main iteration.

        This iteration is normally executed inside the main loop.

        The agent is polling all its sockets for input data. It will wait
        for `poll_timeout`; after this period, the method `iddle` will be
        executed before polling again.

        Returns
        -------
        int
            1 if an error occurred during the iteration (we would expect this
            to happen if an interruption occurs during polling).

            0 otherwise.
        """
        try:
            events = dict(self.poller.poll(self.poll_timeout))
        except zmq.ZMQError as e:
            # Raise the exception in case it is not due to SIGINT
            if e.errno != errno.EINTR:
                raise
            else:
                return 1

        if not events:
            # Agent is iddle
            self.iddle()
            return 0

        if self.rep in events and events[self.rep] == zmq.POLLIN:
            self.process_request()

        # TODO: do not iterate through all sockets
        for s in self.sub_sockets:
            if s in events and events[s] == zmq.POLLIN:
                self.process_publication(s)

        return 0

    def run(self):
        """
        Run the agent.
        """
        if __debug__:
            self.info('Initializing the agent...')
        self.init_agent()

        # Capture SIGINT
        signal.signal(signal.SIGINT, self.sigint_handler)

        if __debug__:
            self.info('REP listening at %s' % (self.rep))
            self.listening = 1

        self.pre()
        self.loop()
        self.post()

        # Terminate agent
        self.terminate()

    def sigint_handler(self, signal, frame):
        """
        Handle interruption signals.
        """
        self.keep_alive = False
        if __debug__:
            self.info('SIGINT captured!')

    def info(self, message):
        cname = str(type(self)).split('.')[-1]
        print('%s {%s} %s' % (cname, self.sock, message))

    def error(self, message):
        cname = str(type(self)).split('.')[-1]
        sys.stderr.write('%s {%s} ERROR! %s\n' % (cname, self.sock, message))
        self.keep_alive = False

    def warn(self, message):
        cname = str(type(self)).split('.')[-1]
        sys.stderr.write('%s {%s} WARNING! %s\n' % (cname, self.sock, message))

    def get_request(self):
        """
        Get request from a client.

        Returns
        -------
        request : list
            Request received from the client.
        """
        try:
            request = self.rep.recv_pyobj()
            if __debug__:
                if type(request) != Message:
                    self.warn('Request is not a Message')
                    request = Message(mType.WRONGTYPE)
                self.listening = 0  # Client waiting for a reply
            return request
        except zmq.ZMQError as e:
            self.error('recv() failed with: %s' % e)
            return Message(mType.ERROR, '%s - Get request failed' % type(self))

    def send_reply(self, reply):
        """
        Send reply to the client.

        Parameters
        ----------
        reply : list
            Reply sent back to the client.
        """
        try:
            if __debug__:
                if type(reply) != Message:
                    self.warn('Reply is not a Message')
                    request = Message(mType.WRONGTYPE)
            self.rep.send_pyobj(reply)
            if __debug__:
                self.listening = 1  # Agent waiting for a request
        except zmq.ZMQError as e:
            self.error('send() failed with: %s' % e)

    def terminate(self):
        """
        Terminating method.
        """
        if __debug__:
            self.info('Closing sockets...')
        self.rep.close()
        self.pub.close()
        self.pull.close()
        if __debug__:
            self.info('Terminated!')

    def clean_list(self, l):
        for i in range(len(l)):
            if isinstance(l[i], (zmq.Context, zmq.Socket)):
                l[i] = str(l[i])

    def clean_dict(self, d):
        for key in d:
            if isinstance(d[key], (zmq.Context, zmq.Socket)):
                d[key] = str(d[key])
            if isinstance(d[key], list):
                self.clean_list(d[key])
            if isinstance(d[key], dict):
                self.clean_dict(d[key])

    def handle(self, request):
        """
        Handle incoming requests.

        The request is passed as parameter to this function.
        This function should always send back a reply to the client before
        returning.

        Parameters
        ----------
        request : Message
            Request received.
        """
        if request.typ == mType.REQATT:
            self.wait_on()
            return
        if request.typ == mType.REQMEM:
            self.send_reply(Message(mType.DICT, self.memory))
            return
        if request.typ == mType.STATUS:
            self.send_reply(Message(mType.DICT, self.status()))
            return
        if request.typ == mType.DIE:
            if __debug__:
                self.info("Received the order to kill myself. Bye.")
            self.keep_alive = False
            self.send_reply(Message(mType.ACK))
            return
        if request.typ == mType.PING:
            self.send_reply(Message(mType.PONG))
            return
        if request.typ == mType.TEST:
            self.send_reply(Message(mType.OK))
            return
        if request.typ == mType.DUMP:
            self.send_reply(Message(mType.PYOBJ, pprint.pformat(vars(self))))
            return
        if request.typ == mType.SAVESTATE:
            if self.save_state(request.data):
                self.send_reply(Message(mType.ACK))
            else:
                self.send_reply(Message(mType.ERROR, 'Could not save state!'))
            return
        if request.typ == mType.GETSTATE:
            self.send_reply(Message(mType.PYOBJ, self.state()))
            return
        if request.typ == mType.REMOTEEXEC:
            if __debug__:
                self.info("ADMIN: Remote execution requested: {}".format(
                          request.data))
            try:
                method = request.data[0]
                if len(request.data) > 1:
                    params = request.data[1:]
                else:
                    params = ()
                fn = getattr(self, method)
                if len(params) > 0:
                    result = fn(params)
                else:
                    result = fn()
                return Message(mType.PYOBJ, result)
            except Exception as e:
                print(str(e))
                print("Remote Execution failed: {}".format(request))

        # Unknown request received
        self.send_reply(Message(mType.UNKNOWN))
        return

    def pre(self):
        pass

    def post(self):
        pass

    def status(self):
        # TODO: review status method...
        status = {}
        status['rpp'] = self.rpp
        return status

    def state(self):
        """
        To be implemented for each class.

        Returns
        -------
        Anything
            Could be a dictionary, or anything, containing the state of
            the agent.
        """
        return None

    def save_state(self, output):
        """
        Save the state of the agent, as returned by the output of the
        `state()` method.

        The state will be dumped to a file using pickle.

        Parameters
        ----------
        output : str
            Output file where the state is to be saved.

        Returns
        -------
        bool
            Whether the state was successfuly saved into the file.
        """
        if not output:
            self.warn('Cannot save state: no output file defined!')
            return False
        state = self.state()
        if not state:
            self.warn('Cannot save state: state() method not implemented!')
            return False
        pickle.dump(state, open(output, 'wb'))
        self.info('Saved state in: %s' % output)
        return True

    def dump(self):
        res = ''
        res += "-----------------------------------------\n"
        res += "- DUMP OBJECT                           -\n"
        res += "-----------------------------------------\n"
        res += pprint.pformat(vars(self))
        self.send_reply(Message(mType.PYOBJ, res))


class TryAutoREP(Agent):
    """
    Accepts incoming requests from clients and sends an automatic response
    to them. All requests are stored in a list.

    Parameters
    ----------
    host : string
        Agent's socket host.
    port : integer
        Agent's socket port.
    """
    def __init__(self, rpp=AgentRPP(), queue=None):
        Agent.__init__(self, rpp, queue)
        self.reqlog = []

    def get_request(self):
        """
        Get request from a client.

        Returns
        -------
        request : list
            Request received from the client.
        """
        req = Agent.get_request(self)
        self.reqlog.append(req)
        return req

    def handle(self, request):
        """
        Handle incoming requests.

        Parameters
        ----------
        Request : object
            Request received.
        """
        if request.typ == mType.CONSULT:
            self.send_reply(Message(mType.LIST, self.reqlog))
            return
        if request.typ == mType.DIE:
            if __debug__:
                self.info("Received the order to kill myself. Bye.")
            self.keep_alive = False
            self.send_reply(Message(mType.ACK))
            return
        if request.typ == mType.PING:
            self.send_reply(Message(mType.PONG))
            return
        self.send_reply(Message(mType.ACK))
        return
