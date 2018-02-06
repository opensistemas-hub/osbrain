.. _advanced_communication_patterns:


*******************************
Advanced communication patterns
*******************************

Some advanced communication patterns are also implemented in osBrain. They are
called channels, rather than sockets, as they are formed with multiple sockets.


.. index:: async-req-rep
.. _async_req_rep:

Asynchronous Request-Reply channel
==================================

An asynchronous request-reply channel is very similar to a normal request-reply
pattern, only in this case we want to process the reply asynchronously (i.e.:
assign a handler for this reply and forget about it until it is received).

This means that, when using an asynchronous request-reply channel, a handler
must be specified for both the replier and the requester.

Example
-------

See the following example in which Bob sends an asynchronous request to Alice.
Note that:

- When Alice binds, she uses ``ASYNC_REP`` instead of ``REP``.
- Bob is assigned a handler too to process Alice's reply when it is received.
- Bob sends the request and is automatically freed. It can log messages or do
  other stuff.
- When the reply is received, Bob automatically processes it.

.. literalinclude:: ../../examples/async_req_rep.py

That is the most basic example, but channels are a bit more flexible. When
sending an asynchronous request we may want to manually specify a handler for
the reply. This will overwrite the default handler specified when connecting to
the ``ASYNC_REP`` server. Try changing the ``.send()`` call::

   def deaf(agent, message):
       agent.log_info('I am deaf...')


   bob.send('alice', 'Hello, Alice!', handler=deaf)

We can also specify a maximum wait time for the reply and some code to be
executed in case the reply was not received after that time. Try the example
above, but setting ``wait=0.5``::

   def no_reply_in_time(agent):
       agent.log_warning('No reply received!')


   bob.send('alice', 'Hello, Alice!', wait=0.5, on_error=no_reply_in_time)

.. note:: If ``on_error`` is not specified, by default the agent will simply
   log a warning.


.. index:: sync-pub-sub
.. _sync_pub_sub:

Synced Publish-Subscribe channel
================================

Another common use case is the synced publish-subscribe channel. It is similar
to the normal publish-subscribe pattern but has some extra functionality. The
server is configured to publish messages through a ``PUB`` socket and clients
can connect to it to receive these messages. Using the synced publish-subscribe
channel, however, allows the clients to send requests to the publisher.

This can be really useful when we want to share some data from the publisher
with all the subscribers but we want the subscribers to be able to interact
(and perhaps even modify) this data.

.. note:: Synchronization is possible because all replies are sent to the
   requester through the same PUB-SUB socket as the one used for normal
   publications. Note that, even though this reply is sent through the PUB-SUB
   socket, it will only be received by the requester and not by any other
   subscribed client.

Example
-------

In the following example we have:

- A synced publisher that requires a handler for requests when binding.
- Two subscribers that connect to the publisher and subscribe to all topics.
- The publisher starts sending publications, which are received in both
  subscribers.
- At some point one of the clients makes a request, which is processed by the
  publisher. The client asynchronously receives and processes the reply from
  the publisher. Only the agent that made the request receives this message.

.. literalinclude:: ../../examples/sync_pub_sub.py

.. note:: Even though we have not used topic filtering in this example, you can
   definitely make use of it, just like with a normal publish-subscribe
   pattern.

Just like with `async_req_rep`, you can further customize the requests by
specifying a maximum wait time and a function/method to be executed in case no
reply was received after that wait time.
