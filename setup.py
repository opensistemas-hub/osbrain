"""
Setup module.
"""
from os import path
from setuptools import setup


with open(path.join(path.abspath(path.dirname(__file__)), 'README.md')) as f:
    long_description = f.read()

setup(
    name='osbrain',
    version='0.1.0',
    description='A general-purpose multi-agent-system module',
    long_description=long_description,
    url='', # TODO
    author='Miguel Sánchez de León Peque',
    author_email='msdeleon@opensistemas.com',
    license='AGPL',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    keywords='osbrain multi-agent system',
    packages=['osbrain'],
    install_requires=['Pyro4>=4.45', 'pyzmq>=15.2.0'],
    extras_require={
        'dev': ['dill'],
        'test': ['pytest'],
    },
)
