#!/usr/bin/env python3

from os import path

from setuptools import setup, find_packages

import libmonzo

def run_setup():
    """Run package setup."""
    here = path.abspath(path.dirname(__file__))

    # Get the long description from the README file
    try:
        with open(path.join(here, 'README.md')) as f:
            long_description = f.read()
    except:
        # This happens when running tests
        long_description = None

    setup(
        name='libmonzo',
        version=libmonzo.__version__,
        description='An API wrapper around Monzo bank accounts.',
        long_description=long_description,
        long_description_content_type="text/markdown",
        url='https://github.com/dalemyers/libmonzo',
        author='Dale Myers',
        author_email='dale@myers.io',
        license='MIT',
        install_requires=[],
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Intended Audience :: Developers',
            'Intended Audience :: Financial and Insurance Industry',
            'Intended Audience :: Information Technology',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.7',
            'Topic :: Office/Business :: Financial',
            'Topic :: Software Development :: Libraries'
        ],

        keywords='bank, banks, monzo, mondo',
        packages=find_packages(exclude=['docs', 'tests'])
    )

if __name__ == "__main__":
    run_setup()
