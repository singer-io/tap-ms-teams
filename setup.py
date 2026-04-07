#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='tap-ms-teams',
      version='0.0.2',
      description='Singer.io tap for extracting data from the Microsofts Teams Graph API',
      author='scott.coleman@bytecode.io',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['tap_ms_teams'],
      install_requires=[
          'singer-python==6.7.0',
          'backoff==2.2.1',
          'requests==2.32.5',
          'urllib3>=2.6.3',
          'pyhumps==3.8.0'
      ],
      extras_require={
          'dev': [
              'pylint',
              'ipdb'
          ]
      },
      python_requires='>=3.9',
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
