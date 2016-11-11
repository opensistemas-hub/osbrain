:mod:`osbrain` --- Main API package
===================================

.. module:: osbrain

:mod:`osbrain` is the main package of osBrain. It imports most of the other
packages that it needs and provides shortcuts to the most frequently used
objects and functions from those packages. This means you can mostly just
``import osbrain`` in your code to start using osBrain.

The classes and functions provided are:

=================================== =========================================
symbol in :mod:`osbrain`            referenced location
=================================== =========================================
.. py:class:: Agent                 :class:`osbrain.agent.Agent`
.. py:function:: run_agent          :func:`osbrain.agent.run_agent`
.. py:function:: run_nameserver     :func:`osbrain.nameserver.run_nameserver`
.. py:class:: Proxy                 :class:`osbrain.proxy.Proxy`
.. py:class:: NSProxy               :class:`osbrain.proxy.NSProxy`
.. py:class:: Logger                :class:`osbrain.logging.Logger`
.. py:function:: run_logger         :func:`osbrain.logging.run_logger`
.. py:class:: SocketAddress         :class:`osbrain.address.SocketAddress`
.. py:class:: AgentAddress          :class:`osbrain.address.AgentAddress`
=================================== =========================================


.. seealso::

   Module :mod:`osbrain.agent`
      The agent classes and functions.

   Module :mod:`osbrain.nameserver`
      The name server logic.

   Module :mod:`osbrain.proxy`
      The proxy classes and functions.

   Module :mod:`osbrain.address`
      The address classes and functions.

   Module :mod:`osbrain.logging`
      The logging classes and functions.
