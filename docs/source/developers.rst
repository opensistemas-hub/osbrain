.. index:: developers

.. _security:

**********
Developers
**********

.. index::
    double: developers; tests

Running the tests
=================

Running the tests locally is very simple, using
`Tox <https://tox.readthedocs.io/>`_ from the top level path of the project:

.. code-block:: bash

   tox

That single command will run all the tests for all the supported Python
versions available in your system or environment.

For faster results you may want to run all the tests just against a single
Python version. This command will run all tests against Python 3.5 only:

.. code-block:: bash

   tox -e py35

Note that those tests include style and static analysis checks. If you just
want to run all the behavior tests (not recommended):

.. code-block:: bash

   pytest -n 8

If you just want to run a handful of behavior tests (common when developing
new functionality), just run:

.. code-block:: bash

   pytest -k keyword

.. note:: Before submitting your changes for review, make sure all tests pass
   with `tox`, as the continuous integration system will run all those checks
   as well.
