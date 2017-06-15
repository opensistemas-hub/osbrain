|logo|

|build| |version| |documentation|
|codeclimate| |codecov|
|requirements|

osBrain is a **general-purpose multi-agent system module** written in
Python and developed by `OpenSistemas <http://www.opensistemas.com>`__.
Agents run independently as system processes and communicate with each
other using message passing.

osBrain uses `ØMQ <http://zeromq.org/>`__ for efficient and flexible
message passing between agents. It also uses
`Pyro4 <https://pythonhosted.org/Pyro4/>`__
to ease the configuration and deployment of complex systems.

Please read the
`osBrain documentation <https://osbrain.readthedocs.io/en/stable/>`__
for a bit more detailed introduction.

osBrain is licensed under the
`Apache License <https://osbrain.readthedocs.io/en/stable/license.html>`__.

-  `Documentation <https://osbrain.readthedocs.io/en/stable/>`__.
-  `osBrain on Pypi <https://pypi.python.org/pypi/osbrain>`__.


Installing osBrain
==================

osBrain requires Python 3. Most probably, Python 3 is already packaged
for your favorite distribution (and maybe even installed by default in your
system). If you do not have Python 3 available, consider using
`Conda <http://conda.pydata.org/miniconda.html>`__ to create a virtual
environment with Python 3.

Installing osBrain is very simple with ``pip``:

.. code-block:: bash

   pip install osbrain

You should now be able to import ``osbrain`` from a python console:

.. code-block:: python

   >>> import osbrain


Code examples
=============

If you want to learn how to use osBrain, refer to the
`tutorial in the documentation <https://osbrain.readthedocs.io/en/stable/>`__
for a set of step-by-step simple code examples.


What can you use osBrain for?
=============================

osBrain has been successfully used to develop a real-time automated-trading
platform in `OpenSistemas <http://www.opensistemas.com>`__, but being a
general-purpose multi-agent system, it is not limited to this application.
Other applications include:

-  Transportation.
-  Logistics.
-  Defense and military applications.
-  Networking.
-  Load balancing.
-  Self-healing networks.

In general, osBrain can be used whenever a multi-agent system architecture
fits the application well:

-  Autonomy of the agents.
-  Local views.
-  Decentralization.


.. |logo| image:: https://cdn.rawgit.com/opensistemas-hub/osbrain/master/docs/source/_static/osbrain-logo-name.svg
.. |build| image:: https://api.travis-ci.org/opensistemas-hub/osbrain.svg?branch=master
   :target: https://travis-ci.org/opensistemas-hub/osbrain
   :alt: Build status badge
.. |version| image:: https://img.shields.io/pypi/v/osbrain.svg
   :target: https://pypi.python.org/pypi/osbrain/
   :alt: Latest version badge
.. |documentation| image:: https://readthedocs.org/projects/osbrain/badge/?version=stable
   :target: http://osbrain.readthedocs.io/en/stable/
   :alt: Documentation badge
.. |codeclimate| image:: https://codeclimate.com/github/opensistemas-hub/osbrain/badges/gpa.svg
   :target: https://codeclimate.com/github/opensistemas-hub/osbrain
   :alt: Code Climate badge
.. |codecov| image:: https://codecov.io/github/opensistemas-hub/osbrain/coverage.svg?branch=master
   :target: https://codecov.io/github/opensistemas-hub/osbrain
   :alt: Coverage (codecov) badge
.. |requirements| image:: https://requires.io/github/opensistemas-hub/osbrain/requirements.svg
   :target: https://requires.io/github/opensistemas-hub/osbrain/requirements/
   :alt: Requirements badge
