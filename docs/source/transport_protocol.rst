.. index:: transport, protocol
.. _transport_protocol:


******************
Transport protocol
******************


.. index:: transports

Available transports
====================

Althought the default transport protocol is IPC for operating systems that
provide UNIX domain sockets and TCP for the rest, there are other transport
protocols that can be used in osBrain:

- ``tcp``: common `TCP <https://en.wikipedia.org/wiki/Transmission_Control_Protocol>`_. Can always be used, and must be used to communicate agents running in
  different machines.
- ``ipc``: common `IPC <https://en.wikipedia.org/wiki/Inter-process_communication>`_. It is the default and the best suited for communication between agents that
  run on the same machine
- ``inproc``: for in-process communication (between threads). The fastest
  protocol, although it is limited to communication between threads that share
  the same :attr:`Agent.context <osbrain.agent.Agent.context>`

The transport protocol can be changed on a per-socket basis, per-agent basis
and also globally.


.. index:: change, transport

Changing the transport
======================

It is possible to change the default global transport protocol by setting
the ``osbrain.config['TRANSPORT']`` configuration variable. So, for example, to
set TCP as the default transport, we could set:

.. code-block:: python

   osbrain.config['TRANSPORT'] = 'tcp'

We can also set the default transport that a particular agent should use by
default by passing the ``transport`` parameter to
:func:`run_agent <osbrain.agent.run_agent>`:

.. code-block:: python

   agent = run_agent('a0', transport='tcp')

If we do not want to change the global default nor any agent's default, then
we can still change the transport protocol when binding, passing the
``transport`` parameter again:

.. code-block:: python

   agent = run_agent('a0')
   agent.bind('PULL', transport='inproc')

.. note:: It is also possible to change the global default transport protocol
   setting the ``OSBRAIN_DEFAULT_TRANSPORT`` environment variable.
