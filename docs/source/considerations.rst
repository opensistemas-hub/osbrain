**************
Considerations
**************


Clients versus servers
======================

When using :ref:`basic_communication_patterns` we have a lot of flexibility:

- We are allowed to connect multiple clients to a server.
- The server can play any role (i.e.: does not need to be always ``REP``, but
  can be ``REQ`` as well). Servers are only defined by the action of binding,
  not by the role they play in the communication pattern.

For example, if we bind using ``PUSH`` and we connect multiple clients to
this server, then messages pushed will be distributed among the clients in a
`Round-robin fashion <https://en.wikipedia.org/wiki/Round-robin_scheduling>`_,
which means the first message will be received by the first client, the
second message will be received by the second client, and so on.

If we bind using ``PULL`` and we connect multiple clients to this server,
then messages pushed will all be received by the single server, as expected.

For more information simply refer to the
`ØMQ guide <http://zguide.zeromq.org/page:all>`_.


Closing connections
===================

For closing a specific connection from an agent we need to call the
``close()`` method, which takes the alias of the socket from the
connection we want to close as a parameter.

.. code-block:: python

   agent.bind('PUB', alias='connection')
   ...
   agent.close('connection')

There is also a ``close_all()`` method, which takes no parameters and
will close all user-defined connections of the agent.

Remember that the `linger` value from the osBrain configuration will
be used for the actual `socket.close()` calls in both methods. For more
information, simply refer to the
`ØMQ guide <http://zguide.zeromq.org/page:all>`_.

.. note:: Closing a connection within an agent will have no effect on
   any possible agents at the other end of the connection. Remember to
   manually close them as well if the connection is not going to be reused.


Adding new methods
==================

Note that proxies can not only be used to execute methods remotely in the
agent, but they can also be used to add new methods or change already
existing methods in the remote agent.

In the following example you can see how we can create a couple of functions
that are then added to the remote agent as new methods.

In order to add new methods (or change current methods) we only need to call
``set_method()`` from the proxy.

.. literalinclude:: ../../examples/add_method.py

Note that ``set_method()`` accepts any number of parameters:

- In case they are not named parameters, the function names will be used as
  the method names in the remote agent.
- In case they are named parameters, then the method in the remote agent will
  be named after the parameter name.


Lambdas
=======

osBrain uses :py:mod:`cloudpickle` when communicating with remote agents
through a proxy. This means that almost anything can be serialized to an agent
using a proxy.

In order to further simplify some tasks, lambda functions can be used to
configure remote agents:

.. literalinclude:: ../../examples/req_rep_lambda.py

See the similarities between this example and the one showed in
:ref:`request_reply`.
In fact, the only difference is the binding from Alice, in which we are using
a lambda function for the handler.


.. _shutting_down:

Shutting down
=============

If we want to end the execution of a specific agent in our system, we can do
it by calling the `agent.shutdown` method:

.. literalinclude:: ../../examples/shutdown.py

Shutting down a name server will result in all agents registered in that name
server being shut down as well. This allows us to easily shutdown groups of
agents at the same time.

.. note:: We can establish connections between agents registered in different
   name servers.


.. _oop:

OOP
===

Although the approach of using proxies for the whole configuration process is
valid, sometimes the developer may prefer to use OOP to define the behavior of
an agent.

This, of course, can be done with osBrain:

.. literalinclude:: ../../examples/push_pull_inherit.py

Most of the code is similar to the one presented in the :ref:`push_pull`
example, however you may notice some differences:

#. When running *Alice*, a new parameter ``base`` is passed to the
   :func:`osbrain.run_agent` function. This means that, instead of
   running the default agent class, the user-defined agent class will be used
   instead. In this case, this class is named ``Greeter``.
#. The ``Greeter`` class implements two methods:

   #. ``on_init()``: which is executed on initialization and will, in this
      case, simply bind a ``'PUSH'`` communication channel.
   #. ``hello()``: which simply logs a *Hello* message when it is executed.
#. When connecting *Bob* to *Alice*, we need the address where *Alice* binded
   to. As the binding was executed on initialization, we need to use the
   ``addr()`` method, which will return the address associated to the alias
   passed as parameter (in the example above it is ``main``).
#. When setting a handler that is a method already defined in the agent we
   simply pass a string with the method name.


Setting initial attributes
==========================

Many times, after spawning an agent, we want to set some attributes, which
may be used to configure the agent before it starts working with the rest of
the multi-agent system:

.. code-block:: python

   a0 = run_agent('foo')
   a0.set_attr(x=1, y=2)

It is such a common task that a parameter ``attributes`` can be used when
running the agent for exactly that:

.. code-block:: python

   a0 = run_agent('foo', attributes=dict(x=1, y=2))

As you can see, this parameter accepts a dictionary in which the keys are the
name of the attributes to be set in the agent and the values are the actual
values that this attributes will take.

.. note:: If you find yourself setting a lot of attributes through a proxy
   then you might use `oop` instead (set attributes on initialization or
   create a method for that purpose).


.. _creating_proxies_to_existing_name_servers:

Creating proxies to existing name servers
=========================================

Many times, specially if we are not working with distributed systems, we want
to spawn a single name server and run all the agents from a single script. If
that is the case, simply by executing the `run_nameserver` function we would
obtain a proxy to the name server.

Sometimes, however, we may need to access name servers that are already
running and of which we do not have a proxy available. To do so, we definitely
need to know the address of the name server, so make sure you spawn it with
a well-known address or save it somewhere to read it later.

You can create a proxy to an already-running name server using the `NSProxy`
class:

.. code-block:: python

   from osbrain import NSProxy


   ns = NSProxy(nsaddr='127.0.0.1:1234')

Note how we need to specify the name server address.

.. note:: This might be useful for attaching yourself to an already-running
   system for manual configuration/update, debugging... If you are just
   planning to launch and configure your architecture from multiple scripts,
   then think it twice, as normally you would not need to do so.
