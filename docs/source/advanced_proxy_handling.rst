.. index:: advanced, proxy


***********************
Advanced proxy handling
***********************


.. note:: Before reading this section make sure you have already understood
   :ref:`agents_and_proxies`.

.. index:: proxy

Understanding proxies better
============================

When an agent is run, there is one thread executing the method
:any:`Agent.run`, which simply listens forever for incoming messages to
process them. At the same time, the :class:`Agent <osbrain.agent.Agent>`
object is served so it can be accessed through proxies.

In order to prevent concurrent access to the agent, proxy calls are by default
serialized and sent to the main thread to be executed there. This way we avoid
any concurrent access to memory (only the main thread will make changes to the
agent).

However, the user has control and can change that default behavior.

.. warning:: The user can decide to change the default behavior and make unsafe
   calls. However, they should be aware of the possible risks they may bring.
   If not carefully selected, unsafe calls can lead to undefined behavior and
   hard-to-debug problems.


.. index:: proxy, unsafe

Executing unsafe calls
======================

You can change the default behavior and make unsafe calls, which means the
method call will be executed on another thread separate from the main thread.
In order to do so, the :class:`Proxy <osbrain.proxy.Proxy>` provides us with
access to the ``safe`` and ``unsafe`` attributes, which allows us to force
safe or unsafe calls for single remote method calls:

.. code-block:: python

   agent = run_agent('test')

   agent.unsafe.method_call()  # This forces an unsafe method_call()
   agent.safe.method_call()  # This forces a safe method_call()

   agent.method_call()  # This is a default (safe) method_call() again

The :class:`Proxy <osbrain.proxy.Proxy>` behavior can also be changed on a
per-proxy basis, either when executing the :any:`run_agent <agent.run_agent>`
function:

.. code-block:: python

   agent = run_agent('test', safe=False)

   agent.method_call()  # This is now by default an unsafe method_call()

Or when creating a new :class:`Proxy <osbrain.proxy.Proxy>` to the agent:

.. code-block:: python

   run_agent('a0')
   agent = Proxy('a0', safe=False)

   agent.method_call()  # This is now by default an unsafe method_call()

.. note:: It is also possible, although totally unadvisable, to change the
   default proxy behavior globally. Setting the ``OSBRAIN_DEFAULT_SAFE``
   environment variable to ``false`` would result in all proxies making unsafe
   calls by default. Another option is to change the ``osbrain.config['SAFE']``
   configuration variable.


.. index:: proxy, oneway, concurrent

Executing one-way, unsafe calls
===============================

In some situations, you might want to execute unsafe calls in parallel without
waiting for any return. In that case, you can make use of the ``oneway`` proxy
attribute:

.. code-block:: python

   agent_proxy.oneway.method_call()

This method call will return immediately, and the code will be executed in the
remote agent concurrently with the main thread and any other unsafe or one-way
calls.

.. warning:: Do note that ``oneway`` calls are actually executed in a separate
   thread, which means they behave like ``unsafe`` calls. If not used with
   care, this concurrency may result in unexpected hard-to-debug behavior.
