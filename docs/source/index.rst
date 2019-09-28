*******************
osBrain - |version|
*******************

.. image:: _static/osbrain-logo-name.svg
   :align: center
   :alt: osBrain logo


.. index:: abstract

What is osBrain?
----------------
osBrain is a **general-purpose multi-agent system module** written in Python
and developed by `OpenSistemas <https://www.opensistemas.com>`_.
Agents run independently as system processes and communicate with each other
using message passing.

osBrain uses `ØMQ <https://zeromq.org/>`_ for efficient and flexible message
passing between agents. It also uses `Pyro4 <https://pythonhosted.org/Pyro4/>`_
to ease the configuration and deployment of complex systems.

Please read  the :doc:`license`.

* `osBrain on Pypi <https://pypi.org/project/osbrain>`_.
* `Source code on Github <https://github.com/opensistemas-hub/osbrain>`_.


Contents
--------

.. toctree::
   :maxdepth: 2

   about.rst
   introduction.rst
   basic_patterns.rst
   considerations.rst
   timers.rst
   transport_protocol.rst
   serialization.rst
   advanced_proxy_handling.rst
   advanced_patterns.rst
   distributed_systems.rst
   security.rst
   developers.rst
   api.rst
   license.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
