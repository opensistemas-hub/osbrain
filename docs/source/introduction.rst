************************
Introduction and Example
************************


.. index:: installation

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


.. index:: hello world

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


.. index:: agents, proxies

Agents and proxies
==================

An agent, in osBrain, is an entity that runs independly from other agents
in the system. An agent, by default, will simply poll for incoming messages
before executing the code defined by the developer. This means a single agent,
as in the `Hello world!` example, makes little or no sense. Agents in a
multi-agent system start to make sense when connected to each other.

The easiest way to run an agent in an osBrain architecture is by calling the
function :func:`osbrain.run_agent`:

>>> agent = run_agent(...)

This function will spawn a new agent and will return a
:class:`osbrain.Proxy` to it.

Proxies are simply local objects that allow us to easily have access to the
remote agent. The fact that agents are run independently from each other
justifies the need of a proxy.

A proxy allows us to call methods or access attributes of the remote agent in
a very convenient way. See for example the previous call:

>>> agent.log_info('Hello world')

The method ``log_info()`` is implemented in :class:`osbrain.Agent` so,
when this method is called from the proxy, this call is actually being
serialized to the remote running agent and gets executed there. The return
value, if any, is then serialized back and returned by the proxy. So basically
so get the impression of being working with a local object while your code is
executed remotely.


.. index:: name server

The name server
===============

A name server is just like any other agent, so it runs independently, but with
a very specific role. Name servers are used as an address book. This means
other agents can be run in the system and can be registered in the name server
using a human-readable alias. Aliases help us accessing these agents easily
even from remote locations.

Note that when calling the :func:`osbrain.run_agent` function, we are
passing a string parameter. This parameter is the alias the agent will use to
register itself in the name server.

When we run a name server calling the :func:`osbrain.run_nameserver`, we
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
simply using its alias. Then it uses the agent proxy to remotely call a
method to log a `Hello world!` message.
