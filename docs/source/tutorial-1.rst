.. index:: tutorial-1

************
Tutorial - 1
************


Installation
============

This tutorial is a step-by-step introduction to osBrain with examples. In order
to start playing with this module, you only need to install it.

osBrain requires Python 3. Most probably, Python 3 is already packaged for your
favorite distribution (and maybe even installed by default in your system). If
you do not have Python 3 available, consider using
`Conda <http://conda.pydata.org/miniconda.html>`_ to create a virtual
environment with Python 3.

Installing osBrain is very simple with `pip`::

    pip install osbrain

You should now be able to import ``osbrain`` from a python console:

    >>> import osbrain


Hello world
===========

The first example is, of course, a simple *hello world!* program. Three steps
are taken here:

#. Run a name server.
#. Run an agent with an alias ``Example``.
#. Log a ``Hello world`` message from the agent.

.. literalinclude:: ../../examples/hello_world.py

Running this example from your terminal should simply show you a log message
saying `Hello world!` but, what exactly is happening there?


Agents and proxies
==================

An agent, in osBrain, is an entity that runs independly from other agents
in the system. An agent, by default, will simply poll for incoming messages
before executing the code defined by the developer. This means a single agent,
as in the `Hello world!` example, makes little or no sense. Agents in a
multi-agent system start to make sense when connected to each other.

The easiest way to run an agent in an osBrain architecture is by calling the
function :func:`osbrain.core.run_agent`:

>>> agent = run_agent(...)

This function will spawn a new agent and will return a
:class:`osbrain.core.Proxy` to it.

Proxies are simply local objects that allow us to easily have access to the
remote agent. The fact that agents are run independently from each other
justifies the need of a proxy.

A proxy allows us to call methods or access attributes of the remote agent in
a very convenient way. See for example the previous call:

>>> agent.log_info('Hello world')

The method ``log_info()`` is implemented in :class:`osbrain.core.Agent` so,
when this method is called from the proxy, this call is actually being
serialized to the remote running agent and gets executed there. The return
value, if any, is then serialized back and returned by the proxy. So basically
so get the impression of being working with a local object while your code is
executed remotelly.


The name server
===============

A name server is just like another agent, so it runs independently, but with
a very specific role. Name servers are used as an address book. This means
other agents can be run in the system and can be registered in the name server
using a human-readable alias. Aliases help us accessing these agents easily
even from remote locations.

Note that when calling the :func:`osbrain.core.run_agent` function, we are
passing a string parameter. This parameter is the alias the agent will use to
register itself in the name server.

When we run a name server calling the :func:`osbrain.core.run_nameserver`, we
also get in return a proxy to this name server:

>>> ns = run_nameserver()

This proxy can be used to list the agents registered in the name server:

.. literalinclude:: ../../examples/name_server_agents.py

The code above should simply print the aliases of all the agents registered
in the name server.

A name server proxy can also be used to create proxies to registered agents.
This is specially useful when accessing the multi-agent system from a different
console or location, as it will reduce the number of addresses that we need
to remember.

.. literalinclude:: ../../examples/name_server_proxy.py

The code above creates (and registers) three different agents in a name server
and then creates, through the name server proxy, a proxy to one of those agents
simply using its alias. Then it uses the agent proxy to remotelly call a
method to log a `Hello world!` message.


.. _push_pull:

Push-Pull
=========

Now that we understand the basics of how proxies, agents and name servers work,
let us jump into a more interesting example.

As mentioned before, a multi-agent system only makes sense if agents are
connected with each other and share some information using message passing.

In this first example, we will create two agents: *Alice* and *Bob*, and we
will make alice send messages to *Bob* using a simple push-pull communication
pattern.

.. literalinclude:: ../../examples/push_pull.py

So, in this case, we are doing some more stuff. After we spawn *Alice* and
*Bob*, we connect them.

First, we make *Alice* bind:

>>> addr = alice.bind('PUSH', alias='main')

There are three things to remark in that line:

#. The first parameter ``'PUSH'`` represents the communication pattern we want
   to use. In this case we are using a simple push-pull (unidirectional)
   pattern to allow *Alice* to send messages to *Bob*.
#. The second parameter is, once again, an alias. We can use this alias to
   refer to this communication channel in an easier way.
#. The binding, as you already guessed, takes place in the remote agent, but
   it actually returns a value, which is the address the agent binded to. This
   address is serialized back to us so we can use it to connect other agents
   to it.

The next interesting line of code is the one in which *Bob* connects to
*Alice*:

>>> bob.connect(addr, handler=log_message)

There are two things to remark in here:

#. Calling ``connect()`` from an agent requires, first, an address. This
   address is, in this case, the one we got after binding *Alice*. This method
   will automatically select the appropriate communication pattern to connect
   to this pattern (``'PULL'`` in this case).
#. *Bob* will be receiving messages from *Alice*, so we must set a handler
   function that will be executed when a message from *Alice* is received.
   This handler will be serialized and stored in the remote agent to be
   executed there when needed.

The handler function, in its most basic form, accepts two parameters::

   def handler(agent, message):
       ...

#. The actual agent (can be named ``self`` as well, in an OOP way).
#. The message that is received.

In the example above, the handler simply logs the message received.


.. _req_rep:

Request-Reply
=============

Another common communication pattern is the request-reply, in which a requester
sends a message to the replier and expects always a reply back. It is sometimes
useful, specially when some kind of synchronization is required.

.. literalinclude:: ../../examples/req_rep.py

The main difference with respect to the push-pull pattern is that, in this
case, Bob must run the ``recv`` method in order to get the reply back from
Alice.

.. note:: Although the requester is not required to immediately await for the
   reply (i.e.: can do other stuff after sending the request and before receiving
   the response), it is required to receive a reply back before making another
   request through the same communication channel. Multiple requests can be made
   from the same agent as long as it uses different communication channels for
   each request.


Publish-Subscribe
=================

One of the most useful communication patterns between agents is the publish
and subscribe pattern. The publisher will send messages to all subscribed
agents.

Here is an example in which *Alice* is the publisher and *Bob* and *Eve*
subscribe to *Alice*. This way, when *Alice* sends a message, both *Bob* and
*Eve* will receive it:

.. literalinclude:: ../../examples/pub_sub.py

Note the similarities between this example and the Sender-Receiver example.
The only differences are that *Alice* is now binding using the ``'PUB'``
pattern and that, instead of having just *Bob* connecting to *Alice*, we now
have *Eve* as well connecting to *Alice*.

This communication pattern allows for easy filtering. Refer to the
:ref:`filtering` section in the tutorial for more details.
