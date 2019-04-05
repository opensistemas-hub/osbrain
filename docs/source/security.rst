.. index:: security

********
Security
********

.. warning::
   osBrain should be considered unsafe when used with remote machines. This
   package has some security risks. Understanding the risks is very important
   to avoid creating systems that are very easy to compromise by malicious
   entities.


.. index::
    double: security; serialization

Serialization in osBrain
========================
osBrain can use different serializers when passing messages between agents and
when configuring and deploying the multi-agent architectures. Among this
serializers, some are considered unsafe (:py:mod:`pickle`,
:py:mod:`cloudpickle`...).

Using these unsafe serializers is a security risk. The main problem is that
allowing a program to deserialize arbitrary data can cause arbitrary code
execution and this may wreck or compromise your system. Therefore, osBrain is
meant to be run only within trusted networks (i.e.: LANs) or with properly
encrypted/safe communications (see `Protocol encryption`_).


.. index::
    double: security; network interfaces

Network interface binding
=========================
By default osBrain binds every server on localhost, to avoid exposing things
on a public network or over the internet by mistake. If you want to expose your
osBrain agents to anything other than localhost, you have to explicitly tell
osBrain the network interface address it should use. This means it is a
conscious effort to expose agents to remote machines.


.. index::
    double: security; encryption

Protocol encryption
===================
osBrain doesn't encrypt the data it sends over the network. This means you
must not transfer sensitive data on untrusted networks (especially user data,
passwords, and such) because it is possible to eavesdrop. Either encrypt the
data yourself before passing, or run osBrain over a secure network (VPN or
SSH tunnel).
