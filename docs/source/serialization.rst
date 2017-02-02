.. index:: serialization

.. _serialization:

********
Serialization
********

Serialization in osBrain
========================
Data needs to be serialized in order to be sent from one osBrain agent to
another.

osBrain has two options for serializing the data. One is through the use
of :py:mod:`pickle` and the other one is the `'raw'` option, in which bytes
are directly sent.

For internal communication, `pickle` is the default option. The programmer
might specify which option to use when binding a socket.

osBrain uses :py:mod:`pickle` module for serialization when passing messages
between agents internally and can use :py:mod:`pickle` and :py:mod:`dill` for
serialization when configuring and deploying the multi-agent architectures.
It is well known that using pickle or dill for this purpose is a security risk.
The main problem is that allowing a program to unpickle or undill arbitrary
data can cause arbitrary code execution and this may wreck or compromise your
system.