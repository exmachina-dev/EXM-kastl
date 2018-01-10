# -*- coding: utf-8 -*-

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

import codecs

__version__ = '2.1.0'

def file_content(filename):
    return codecs.open(filename, 'r', 'utf-8').read()

setup(
    name='kastl',
    version=__version__,
    packages = find_packages(),
    description="Kastl motion server software by ExMachina SAS.",
    long_description=file_content('README.md'),
    author="Benoit Rapidel, ExMachina SAS",
    author_email="benoit.rapidel+devs@exmachina.fr",
    url="http://github.org/exmachina-dev/EXM-kastl.git",
    package_data={'': ['LICENSE']},
    include_package_data=True,
    install_requires=[],
    license=file_content('LICENSE'),
    platforms = ["Beaglebone"],
    entry_points = {
        'console_scripts': [
            'kastl = kastl.kastl:main'
        ]
    },
    classifiers=(
        'Development Status :: 2 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ),
)
