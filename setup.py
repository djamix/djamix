# coding: utf-8

import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='djamix',
    version='0.1',
    packages=['djamix'],
    include_package_data=True,
    license='MIT License',
    description="Faster mockups and prototypes with django-like environment. "
    "Using django in the background",
    long_description=README,
    # url='https://github.com/djamix/djamix',
    # author='Artur Czepiel',
    # author_email='czepiel.artur+djamix@gmail.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
)
