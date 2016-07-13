"""
Setup module.
"""
import re
from os.path import join as pjoin
from setuptools import setup


with open(pjoin('osbrain', '__init__.py')) as f:
    line = next(l for l in f if l.startswith('__version__'))
    version = re.match('__version__ = [\'"]([^\'"]+)[\'"]', line).group(1)

setup(
    name='osbrain',
    version=version,
    description='A general-purpose multi-agent-system module',
    long_description='''A general-purpose multi-agent-system module written
        in Python. It uses ZeroMQ for flexible and efficient communications
        between agents and Pyro4 to ease configuration and deployment.''',
    url='https://github.com/opensistemas-hub/osbrain',
    author='Miguel Sánchez de León Peque',
    author_email='msdeleon@opensistemas.com',
    license='Apache License, Version 2.0',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    keywords='osbrain multi-agent system',
    packages=['osbrain'],
    install_requires=['Pyro4==4.45', 'pyzmq>=15.2.0'],
    extras_require={
        'dev': ['dill'],
        'test': ['tox'],
        'docs': ['sphinx', 'numpydoc'],
    },
)
