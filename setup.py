from setuptools import setup, find_packages
import os

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

long_description = read('README.txt') + '\n' +\
    read('CHANGES.txt')

setup(name='hodgepodge',
      version = '0.1',
      description="Distributed component publish/subscribe.",
      long_description=long_description,
      long_description_content_type="text",
      classifiers=['Development Status :: 5 - Alpha',
                   'Environment :: Network Environment',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: Lesser General Public License v2.0',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Topic :: Internet :: TCP/IP',
                   'Topic :: Software Development :: Libraries',
                   'Topic :: Component Software',
                   ],
      keywords='publish subscribe library event zope interface zeromq 0mq',
      author='Paul Sephton',
      author_email='prsephton@gmail.com',
      license='LGPL',
      packages=find_packages('src'),
      package_dir = {'': 'src'},
      namespace_packages=[],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'zope.site',
          'zope.interface',
          'zope.schema',
          'zope.component',
          'zope.event',
          'zope.location',
          'zope.container',
          'pyzmq',
          'dill',
         ],
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
         hp_python = hodgepodge.scripts.interpreter:main
      """,
      )
