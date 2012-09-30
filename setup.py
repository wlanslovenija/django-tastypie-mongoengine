#!/usr/bin/env python

import os

from setuptools import setup, find_packages

try:
    # Workaround for http://bugs.python.org/issue15881
    import multiprocessing
except ImportError:
    pass

VERSION = '0.2.4'

if __name__ == '__main__':
    setup(
        name = 'django-tastypie-mongoengine',
        version = VERSION,
        description = "MongoEngine support for django-tastypie.",
        long_description = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read(),
        author = 'Matevz',
        author_email = 'matevz.mihalic@gmail.com',
        url = 'https://github.com/mitar/django-tastypie-mongoengine',
        keywords = "REST RESTful tastypie mongo mongodb mongoengine django",
        license = 'AGPLv3',
        packages = find_packages(exclude=('*.tests', '*.tests.*', 'tests.*', 'tests')),
        classifiers = (
            'Development Status :: 4 - Beta',
            'Environment :: Web Environment',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: GNU Affero General Public License v3',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Framework :: Django',
        ),
        zip_safe = False,
        install_requires = (
            'Django>=1.4',
            'django-tastypie>=0.9.11',
            'mongoengine>=0.6.9',
        ),
        test_suite = 'tests.runtests.runtests',
        tests_require = (
            'Django>=1.4',
            'django-tastypie>=0.9.11',
            'mongoengine>=0.6.9',
        ),
    )
