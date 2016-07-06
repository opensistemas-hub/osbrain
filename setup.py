"""
Setup module.
"""
from setuptools import setup


setup(
    name='osbrain',
    version='0.1.0',
    description='A general-purpose multi-agent-system module',
    long_description='''A general-purpose multi-agent-system module written
        in Python. It uses ZeroMQ for flexible and efficient communications
        between agents and Pyro4 to ease configuration and deployment.''',
    url='',  # TODO
    author='Miguel Sánchez de León Peque',
    author_email='msdeleon@opensistemas.com',
    license='AGPL',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: GNU Affero General Public License v3 ' + \
            'or later (AGPLv3+)',
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
