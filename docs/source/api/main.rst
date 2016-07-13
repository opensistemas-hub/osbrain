:mod:`osbrain` --- Main API package
===================================

.. module:: osbrain

:mod:`osbrain` is the main package of osBrain. It imports most of the other
packages that it needs and provides shortcuts to the most frequently used
objects and functions from those packages. This means you can mostly just
``import osbrain`` in your code to start using osBrain.

The classes and functions provided are:

=================================== ==========================
symbol in :mod:`osbrain`            referenced location
=================================== ==========================
.. py:class:: Agent                 :class:`osbrain.core.Agent`
.. py:function:: run_agent          :func:`osbrain.core.run_agent`
=================================== ==========================


.. seealso::

   Module :mod:`osbrain.core`
      The core osBrain classes and functions.

   Module :mod:`osbrain.nameserver`
      The osBrain name server logic.
