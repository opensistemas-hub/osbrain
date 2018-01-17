.. index:: distributed, systems

*******************
Distributed systems
*******************

.. note:: Before diving into osBrain distributed systems, make sure to read
   and understand the `serialization` and `security` sections.


Name servers
============

Normally you would want to have a centralized name server when working with
distributed systems, but that is not mandatory, for some applications it might
be more convenient to have multiple name servers in different machines, each
handling different agents.

If you want to create a proxy to a remote name server, simply refer to the
`creating_proxies_to_existing_name_servers` section.


.. index:: binding, distributed

Binding with distributed systems
================================

Working with distributed systems is easy, you just basically need to make
sure you use TCP transport and to specify the network interface IP address
that you want to bind to.

This can be done when binding (note that we are using `127.0.0.1` but you
may use any other IP address available in your system):

.. code-block:: python

   address = agent.bind('PULL', transport='tcp', addr='127.0.0.1')

Defining just the IP address means the agent will bind to a random port, which
is usually fine. However, you can also specify the port to bind to:

.. code-block:: python

   address = agent.bind('PULL', transport='tcp', addr='127.0.0.1:1234')

Remember that the default transport can also be changed globally or per-agent
(read the `serialization` section).


Name server, proxies and addresses
==================================

Name servers are very useful, and even more when working with distributed
systems. Where is that agent? Which was that address?

If we have access to a name server through a name server proxy, remember that
we can very easily create a proxy to one of its registered agents:

.. code-block:: python

   agent_proxy = name_server_proxy.proxy('Agent_name')

And then, once we have a proxy to the agent, we can very easily retrieve any
address by its alias:

.. code-block:: python

   address = agent_proxy.addr('address_alias')

As you can see, aliases become specially useful in distributed systems!


.. index:: proxies

Proxies and multiple scripts
============================

With distributed systems, it is very common to have multiple scripts (many
times spread across multiple machines). If those are to interact together,
you should consider whether a single/shared name server should be used. This
simplifies the way you can get proxies to every agent and also the way they
may share information between them.

If you are just starting with distributed systems and osBrain, you may
approach it the following way:

- You create one script, in which you run some agents and configure them.
- You create another script, in which you run some more agents and configure
  those as well.
- From the second script, you access agents that you created on the first
  and expect them to be ready and completely configured. But it turns
  out that might not be the case.

To avoid this issue, try to do all the configuration of agents from a single
script, even if those agents are created from different ones.
Remember that proxies allow you to treat remote agents just like local objects,
which means it does not really matter if they are running in one machine or
another.

.. note:: If you want to make sure the agent is running before using it, you
   can use the `Proxy.wait_for_running()` method.
