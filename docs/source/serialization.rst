.. index:: serialization

.. _serialization:

********
Serialization
********

Serialization in osBrain
========================
osBrain uses :py:mod:`pickle` module for serialization when passing messages
between agents internally and can use :py:mod:`pickle`, :py:mod:`json` and `raw`
serialization (in which raw bytes are sent, hence the name) for serialization
when configuring and deploying the multi-agent architectures. It is well known
that using pickle or json for this purpose is a security risk.
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

Right now, there are two ways in which the serializer can be specified.

The first one is manually specifying it when binding to a socket:

.. literalinclude:: ../../examples/explicit_serializer.py

The other one is through setting the environment variable
`OSBRAIN_DEFAULT_SERIALIZER`. This option is only used if, when binding to a
socket, there is no serializer specified.


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
