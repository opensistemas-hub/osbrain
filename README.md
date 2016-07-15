![][osbrain-logo]

[![Build Status](https://api.travis-ci.org/opensistemas-hub/osbrain.svg?branch=master)](https://travis-ci.org/opensistemas-hub/osbrain)
[![Latest Version](https://img.shields.io/pypi/v/osbrain.svg)](https://pypi.python.org/pypi/osbrain/)
[![Downloads](https://img.shields.io/pypi/d/osbrain.svg)](https://pypi.python.org/pypi/osbrain/)

osBrain is a **general-purpose multi-agent system module** written in Python.
Agents run independently as system processes and communicate with each other
using message passing.

osBrain uses [ØMQ](http://zeromq.org/) for efficient and flexible messsage
passing between agents. It also uses [Pyro4](https://pythonhosted.org/Pyro4/)
to ease the configuration and deployment of complex systems.

Please read the
[osBrain documentation](https://pythonhosted.org/osbrain/introduction.html)
for a bit more detailed introduction.

osBrain is licensed under the
[Apache License](https://pythonhosted.org/osbrain/license.html).

- [Documentation](https://pythonhosted.org/osbrain/).
- [osBrain on Pypi](https://pypi.python.org/pypi/osbrain).


## Installing osBrain

osBrain requires Python 3. Most probably, Python 3 is already packaged for your
favorite distribution (and maybe even installed by default in your system). If
you do not have Python 3 available, consider using
[Conda](http://conda.pydata.org/miniconda.html) to create a virtual environment
with Python 3.

Installing osBrain is very simple with `pip`:

    pip install osbrain

You should now be able to import `osbrain` from a python console:

    >>> import osbrain


## Code examples

If you want to learn how to use osBrain, refer to the
[tutorial in the documentation](https://pythonhosted.org/osbrain/tutorial.html)
for a set of step-by-step simple code examples.


## What can you use osBrain for?

osBrain has been successfully used to develop a real-time automated-trading
platform in [OpenSistemas](http://www.opensistemas.com), but being a
general-purpose multi-agent system, it is not limited to this application.
Other applications include:

- Transportation.
- Logistics.
- Defense and military applications.
- Networking.
- Load balancing.
- Self-healing networks.

In general, osBrain can be used whenever a multi-agent system architecture
fits the application well:

- Autonomy of the agents.
- Local views.
- Decentralization.


[osbrain-logo]: https://cdn.rawgit.com/opensistemas-hub/osbrain/master/docs/source/_static/osbrain-logo-name.svg
