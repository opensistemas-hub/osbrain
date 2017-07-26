.. _basic_communication_patterns:


****************************
Basic communication patterns
****************************


.. index:: push-pull
.. _push_pull:

Push-Pull
=========

Example
-------

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

addr = alice.bind('PUSH', alias='main')

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

bob.connect(addr, handler=log_message)

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

List of handlers
----------------

When using push-pull communication patterns we are allowed to set multiple
handlers using a list. In example:

.. code-block:: python

   agent.connect('PULL', handler=[handler1, handler2, handler3])

Note that in this case all handlers will be executed in sequence.


.. index:: request-reply
.. _request_reply:

Request-Reply
=============

Example
-------

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

Return versus yield
-------------------

The easiest way to reply to a request is to return a value from the handler,
as seen in :ref:`request_reply`::

   def reply(agent, message):
       return 'Received ' + str(message)

However, using ``return`` the agent can only send a response after executing
the handler. Instead, an agent can use `yield` to reply earlier if needed::

   def reply(agent, message):
       yield 'Received' + str(message)  # Reply now
       agent.log_info('Already sent a reply back!')   # Do some stuff later


.. index:: publish-subscribe

Publish-Subscribe
=================

Example
-------

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

.. index:: filtering
.. _filtering:

Filtering
---------

The publish-subscribe pattern is very useful, but it is also very powerful
when combined with filtering.

Any time we publish a message from an agent, a topic can be specified. If a
topic is specified, then only the agents that are subscribed to that topic
will receive the message. This filtering is done in the publisher side,
meaning that the network does not suffer from excessive message passing.

In the following example we have *Alice* publishing messages using topic
``a`` or ``b`` at random. Then we have *Bob* subscribed to both topics, *Eve*
subscribed to topic ``a`` only and *Dave* subscribed to topic ``b`` only.

.. literalinclude:: ../../examples/pub_sub_filter.py

Note how we can specify different handlers for different topics when
subscribing agents.

.. index:: more_on_filtering
.. _more_on_filtering:

More on filtering
-----------------

We can also easily modify the subscriptions at run-time.

In the following example, *Alice* will be publishing messages using topics
``a`` and ``b`` at the same time. Meanwhile, *Bob* will first subscribe to
topic ``a``. After a few seconds, he will subscribe to topic ``b`` while
unsubscribing from topic ``a``.

.. literalinclude:: ../../examples/pub_sub_more_on_filter.py

.. note:: Syntax regarding handlers in the ``subscribe()`` and
   ``unsubscribe()`` methods is the same that the one used when specifying
   the handlers on the ``connect()``/``bind()`` call of the SUB socket.

.. warning:: Calls to the ``subscribe()`` method will always override the
   previous handler for each of the specified topics, if any.
