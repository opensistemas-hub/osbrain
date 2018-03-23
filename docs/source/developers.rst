.. index:: developers


**********
Developers
**********

.. index:: workflow

Workflow
========

We are happy you like osBrain and we would love to receive contributions from
you! Note that contributions do not necessarily need to include code: you can
help `telling us what problems you are having with osBrain <https://github.com/opensistemas-hub/osbrain/issues>`_
or suggesting improvements to the documentation.

If you would like to help us with code, proceed to fork the project, make the
changes you want and then submit a pull request to start a discussion. Take
into account that we follow some rules for development:

- We like to follow style standards (i.e.: PEP8). But do not worry, our test
  suite will help you with that and tell you if you wrote something wrong.
- We like tests, so any new functionality should also include the corresponding
  tests.
- We like documentation, so changes in the code should also include changes
  in the code docstrings and changes in the user documentation if they affect
  how the user may use osBrain.


.. index:: dependencies

Installing dependencies
=======================

To install the required dependencies for developing osBrain, you can
make use of the provided `requirements.txt` file:

.. code-block:: bash

   pip install -r requirements.txt


.. index:: tests

Running the tests
=================

Running the tests locally is very simple, first install
`Tox <https://tox.readthedocs.io/>`_::

   pip install tox

And run it from the top-level path of the project::

   tox

That single command will run all the tests for all the supported Python
versions available in your system or environment.

For faster results you may want to run all the tests just against a single
Python version. This command will run all tests against Python 3.6 only::

   tox -e py36

When running Tox, tests are actually executed with :py:mod:`pytest`. Although
not recommended, you might want to directly use that tool for finer control:

.. code-block:: bash

   pytest -n 8

If you just want to run a handful of behavior tests (common when developing
new functionality), just run:

.. code-block:: bash

   pytest -k keyword

.. note:: Before submitting your changes for review, make sure all tests pass
   with `tox`, as the continuous integration system will run all those checks
   as well.


.. index:: documentation

Generating documentation
========================

Documentation is generated with Sphinx. In order to generate the documentation locally you need to run `make` from the `docs` directory:

.. code-block:: bash

   make html
