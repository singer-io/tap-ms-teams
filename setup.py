#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='tap-ms-teams',
      version='0.0.2',
      description='Singer.io tap for extracting data from the Microsofts Teams Graph API',
      author='scott.coleman@bytecode.io',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['tap_ms_teams'],
      install_requires=[
          'singer-python==5.9.0',
          'backoff==1.8.0',
          'requests==2.23.0',
          'pyhumps==1.6.1'
      ],
      extras_require={
          'dev': [
              'pylint',
              'ipdb',
              'nose',
          ]
      },
      python_requires='>=3.5.2',
      entry_points='''
          [console_scripts]
          tap-ms-teams=tap_ms_teams:main
      ''',
      packages=find_packages(),
      package_data={
          'tap_ms_teams': [
              'schemas/*.json'
          ]
      })
