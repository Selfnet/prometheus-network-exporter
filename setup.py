#!/usr/bin/env python3
"""A setuptools based setup module.

See:
    https://packaging.python.org/en/latest/distributing.html
    https://github.com/pypa/sampleproject
"""

# To use a consistent encoding
import os
from os import path
from prometheus_network_exporter import __version__ as VERSION
# Always prefer setuptools over distutils
from setuptools import setup, find_packages

HERE = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()

setup(
    name='prometheus-network-exporter',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='{}'.format(VERSION),

    description='A Junos Exporter',
    long_description=LONG_DESCRIPTION,

    # The project's main homepage.
    url='https://github.com/Selfnet/prometheus-network-exporter',

    # Author details
    author='Marcel Fest',
    author_email='marcelf@selfnet.de',

    # Choose your license
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Metrics :: NetworkDevices',

        # Pick your license as you wish (should match "license" above)
        'License :: MIT',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3'
    ],

    # What does your project relate to?
    keywords='metric prometheus junos juniper prometheus-junos-exporter',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(
        exclude=['bin', 'lib', 'contrib', 'docs', 'tests', 'prometheus']),

    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    # py_modules=["Multivault"],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['PyYAML', 'tornado', 'junos-eznc==2.2.1', 'arubaos_client', 'unifi_client', 'voluptuous', 'fqdn', 'prometheus-client'],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    extras_require={
        'dev': ['pylint', 'autopep8', 'pep8'],
    },
    package_data={
        'prometheus_network_exporter.views.junos': ['*.yml'],
        'prometheus_network_exporter.config.definitions.junos': ['metrics_definition.yml'],
        'prometheus_network_exporter.config.definitions.unifi': ['metrics_definition.yml']
    },
    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    data_files=[(os.path.join('/etc', 'prometheus-network-exporter'),
                 ['prometheus_network_exporter/config/config.yml'])],
    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
)
