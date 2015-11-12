# osBrain

osBrain is a general-purpose, distributed, scalable multiagent system.

## Setting up the development environment

### Clonning the repository

    git clone ssh://git@imasd.opensistemas.com/osbrain

### Creating a Python virtual environment with `pip`

Managing Python virtual environments is easier with `virtualenvwrapper`:

    sudo dnf install python-virtualenvwrapper

In order to create a virtual environment to work with osBrain:

    mkvirtualenv -p python3 osbrain

Note that the Python interpreter version used is 3. In your system, `python`
may be already python 3; make sure you set the proper Python 3 system
interpreter.

The virtualenvironment is automatically activated. In order to deactivate it,
you must execute `deactivate`. The command `workon` will allow you to activate
it again in the future:

    deactivate
    workon osbrain

### Installing the dependencies within the virtual environment

Always make sure to work within the virtual environment:

    workon osbrain

First, we should make sure `pip` is updated:

    pip install --upgrade pip

Then we can proceed to install all the required modules:

    pip install -r requirements.txt

This process may take some time and may require the installation of some
libraries/packages in our system. Just check for any errors in the process
and try to solve the required dependencies in order to complete the
installation.

### Trying out a simple example

If everything is set up correctly, all the tests should pass:

    py.test -s -v ./

We can also try any example in the `examples` folder.
