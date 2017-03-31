.. index:: serialization

.. _serialization:

********
Serialization
********

Introduction
============
osBrain uses :py:mod:`pickle` module for serialization when passing messages
between agents internally and can use :py:mod:`pickle`, :py:mod:`json` and `raw`
serialization (in which raw bytes are sent, hence the name) for serialization
when configuring and deploying the multi-agent architectures.

It is well known that using pickle or json for this purpose is a security risk.
The main problem is that allowing a program to unpickle or unjson arbitrary
data can cause arbitrary code execution and this may wreck or compromise your
system.

NOTE: Be aware that different serializers might have different limitations.
For example, the `json` method does not support serializing an object of
`bytes` type, while `pickle` does support it.


Defining the serializer
=======================
Specifying the serializer only makes sense in `server` sockets, since `clients`
will automatically detect and set the type they need in order to communicate
accordingly with the server.

There are three ways in which the serializer can be specified:

- Global configuration.
- Specifying it at `per agent` configuration.
- Specifying it at `per socket` configuration.


Global configuration
====================

By setting the ``osbrain.config['SERIALIZER']`` configuration variable, we
can change the default serializer. For example:

.. code:: python

    osbrain.config['SERIALIZER'] = 'json'

.. note:: It is also possible to change the global default serializer by
   setting the ``OSBRAIN_DEFAULT_SERIALIZER`` environment variable.


Per agent configuration
=======================

Specifying the serializer at per agent level will override the global
configuration. This can be done as follows:

.. code:: python

    a1 = run_agent('a1', serializer='json')


Per socket configuration
========================

Finally, we can specify the serializer at per socket level. This will override
any other configuration (global/per agent). For example:

.. code:: python

    a1 = run_agent('a1', serializer='json')
    # Raw serialization will override json for this socket
    addr1 = a1.bind('PUB', 'alias1', serializer='raw')


PUBSUB messaging pattern
========================

For the PUBSUB pattern, there is a special character (`b'\x80'` as of now, even
though it could change at any time) that we use so as to let the agents know
what is the topic and what is the message itself. Note that the special
separator character is only required if there is a topic and the serialization
option is NOT set to `raw` (read below for more information).


Considerations when using `raw` serialization and PUBSUB pattern
================================================================

Special care must be taken when working with `raw` serialization and the PUBSUB
messaging pattern. Under those conditions, we decided to replicate the raw
ZeroMQ PUBSUB communication, in which the topic is sent along with the message
and is the handler the one that must take care of separating the topic from the
message it self.

Note that if we are using other type of serialization, it is safe to assume
that what we are receiving only the original message, without any traces of the
topic.
