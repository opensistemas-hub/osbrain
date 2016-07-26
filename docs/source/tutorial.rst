********
Tutorial
********

.. index:: tutorial

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

.. literalinclude:: ../../examples/hello_world/main.py

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

.. literalinclude:: ../../examples/name_server/agents.py

The code above should simply print the aliases of all the agents registered
in the name server.

A name server proxy can also be used to create proxies to registered agents.
This is specially useful when accessing the multi-agent system from a different
console or location, as it will reduce the number of addresses that we need
to remember.

.. literalinclude:: ../../examples/name_server/proxy.py

The code above creates (and registers) three different agents in a name server
and then creates, through the name server proxy, a proxy to one of those agents
simply using its alias. Then it uses the agent proxy to remotelly call a
method to log a `Hello world!` message.


Sender-Receiver
===============

Now that we understand the basics of how proxies, agents and name servers work,
let us jump into a more interesting example.

As mentioned before, a multi-agent system only makes sense if agents are
connected with each other and share some information using message passing.

In this first example, we will create two agents: *Alice* and *Bob*, and we
will make alice send messages to *Bob* using a simple push-pull communication
pattern.

.. literalinclude:: ../../examples/push_pull/main.py

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


OOP
===

Although the approach of using proxies for the whole configuration process is
valid, sometimes the developer may prefer to use OOP to define the behavior of
an agent.

This, of course, can be done with osBrain:

.. literalinclude:: ../../examples/push_pull_inherit/main.py

Most of the code is similar to the one presented in the example above, however
you may notice some differences:

#. When runing *Alice*, a new parameter ``base`` is passed to the
   :func:`osbrain.core.run_agent` function. This means that, instead of
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


Adding new methods
==================

Note that proxies can not only be used to execute methods remotely in the
agent, but they can also be used to add new methods or change already
existing methods in the remote agent.

In the following example you can see how we can create a couple of functions
that are then added to the remote agent as new methods.

In order to add new methods (or change current methods) we only need to call
``set_method()`` from the proxy.

.. literalinclude:: ../../examples/add_method/main.py

Note that ``set_method()`` accepts any number of parameters:

- In case they are not named parameters, the function names will be used as
  the method names in the remote agent.
- In case they are named parameters, then the method in the remote agent will
  be named after the parameter name.


Publisher-Subscriber
====================

One of the most useful communication patterns between agents is the publish
and subscribe pattern. The publisher will send messages to all subscribed
agents.

Here is an example in which *Alice* is the publisher and *Bob* and *Eve*
subscribe to *Alice*. This way, when *Alice* sends a message, both *Bob* and
*Eve* will receive it:

.. literalinclude:: ../../examples/pub_sub/main.py

Note the similarities between this example and the Sender-Receiver example.
The only differences are that *Alice* is now binding using the ``'PUB'``
pattern and that, instead of having just *Bob* connecting to *Alice*, we now
have *Eve* as well connecting to *Alice*.


Filtering
=========

The publish-subscribe pattern is very useful, but it is also very powerful
when combined with filtering.

Any time we publish a message from an agent, a topic can be specified. If a
topic is specified, then only the agents that are subscribed to that topic
will receive the message. This filtering is done in the publisher side,
meaning that the network does not suffer from excessive message passing.

In the following example we have *Alice* publishing messages using topic
``a`` or ``b`` at random. Then we have *Bob* subscribed to both topics, *Eve*
subscribed to topic ``a`` only and *Dave* subscribed to topic ``b`` only.

.. literalinclude:: ../../examples/pub_sub_filter/main.py

Note how we can specify different handlers for different topics when
subscribing agents.
