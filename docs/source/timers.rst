.. index:: timers

******
Timers
******


Repeated actions
================

Timers can be used to repeat an action after a period of time. To illustrate
this, let us modify the :ref:`push_pull` example a bit and make use of the
:func:`.each() <osbrain.agent.Agent.each>` method:

.. literalinclude:: ../../examples/timer_each.py

Note that if an action takes longer to run than the time available before the
next execution, the timer will simply fall behind.


Delayed actions
===============

Timers can be used to execute an action after a defined time delay using the
:func:`.after() <osbrain.agent.Agent.after>` method:

.. literalinclude:: ../../examples/timer_after.py

Note that if an action takes longer to run than the time available before the
next execution, the timer will simply fall behind.


Stopping timers
===============

When executing the
:func:`.each() <osbrain.agent.Agent.each>`
or
:func:`.after() <osbrain.agent.Agent.after>`
methods, a timer is created and an identifier is returned that can be used
later to refer to that timer (i.e.: for stopping it).

In the following example we can see how the returned identifier and an alias
parameter can be used to identify the timer and stop it calling the
:func:`.stop_timer() <osbrain.agent.Agent.stop_timer>` method:

.. literalinclude:: ../../examples/timer_stop.py

You can call the
:func:`.stop_all_timers() <osbrain.agent.Agent.stop_all_timers>`
method if you would rather simply stop all started timers.

If you want to list the timers that are currently running, you can call the
:func:`.list_timers() <osbrain.agent.Agent.list_timers>`
method.
