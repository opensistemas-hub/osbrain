.. index:: tutorial-2

************
Tutorial - 2
************


Timers
======

Timers can be used to repeat an action after a period of time. To illustrate
this, let us modify the :ref:`push_pull` example a bit:

.. literalinclude:: ../../examples/timer/simple.py

Timers also accept parameters that can be used when execution the action:

.. literalinclude:: ../../examples/timer/params.py

Note that if an action takes longer to run than the time available before the
next execution, the timer will simply fall behind.


OOP
===

Although the approach of using proxies for the whole configuration process is
valid, sometimes the developer may prefer to use OOP to define the behavior of
an agent.

This, of course, can be done with osBrain:

.. literalinclude:: ../../examples/push_pull_inherit/main.py

Most of the code is similar to the one presented in the :ref:`push_pull` example,
however you may notice some differences:

#. When runing *Alice*, a new parameter ``base`` is passed to the
   :func:`osbrain.core.run_agent` function. This means that, instead of
   running the default agent class, the user-defined agent class will be used
   instead. In this case, this class is named ``Greeter``.
#. The ``Greeter`` class implements two methods:

   #. ``on_init()``: which is executed on initialization and will, in this
      case, simply bind a ``'PUSH'`` communication channel.
   #. ``hello()``: which simply logs a *Hello* message when it is executed.

#. When connecting *Bob* to *Alice*, we need the address where *Alice* binded
   to. As the binding was executed on initialization, we need to use the
   ``addr()`` method, which will return the address associated to the alias
   passed as parameter (in the example above it is ``main``).


.. _filtering:

Filtering
=========

The publish-subscribe pattern is very useful, but it is also very powerful
when combined with filtering.

Any time we publish a message from an agent, a topic can be specified. If a
topic is specified, then only the agents that are subscribed to that topic
will receive the message. This filtering is done in the publisher side,
meaning that the network does not suffer from excessive message passing.

In the following example we have *Alice* publishing messages using topic
``a`` or ``b`` at random. Then we have *Bob* subscribed to both topics, *Eve*
subscribed to topic ``a`` only and *Dave* subscribed to topic ``b`` only.

.. literalinclude:: ../../examples/pub_sub_filter/main.py

Note how we can specify different handlers for different topics when
subscribing agents.


Adding new methods
==================

Note that proxies can not only be used to execute methods remotely in the
agent, but they can also be used to add new methods or change already
existing methods in the remote agent.

In the following example you can see how we can create a couple of functions
that are then added to the remote agent as new methods.

In order to add new methods (or change current methods) we only need to call
``set_method()`` from the proxy.

.. literalinclude:: ../../examples/add_method/main.py

Note that ``set_method()`` accepts any number of parameters:

- In case they are not named parameters, the function names will be used as
  the method names in the remote agent.
- In case they are named parameters, then the method in the remote agent will
  be named after the parameter name.
