#!/usr/bin/env python

import os

from setuptools import setup, find_packages

try:
    # Workaround for http://bugs.python.org/issue15881
    import multiprocessing
except ImportError:
    pass

VERSION = '0.4.7'

if __name__ == '__main__':
    setup(
        name = 'django-tastypie-mongoengine',
        version = VERSION,
        description = "MongoEngine support for django-tastypie.",
        long_description = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read(),
        author = 'wlan slovenija',
        author_email = 'open@wlan-si.net',
        url = 'https://github.com/wlanslovenija/django-tastypie-mongoengine',
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
            'Django>=1.5',
            'django-tastypie>=0.9.12',
            'mongoengine>=0.8.1',
            'python-dateutil>=2.1',
            'lxml',
            'defusedxml',
            'PyYAML',
            'biplist',
            'python-mimeparse>=0.1.4',
        ),
        test_suite = 'tests.runtests.runtests',
        tests_require = (
            'Django>=1.5',
            'django-tastypie>=0.9.12',
            'mongoengine>=0.8.1',
            'python-dateutil>=2.1',
            'lxml',
            'defusedxml',
            'PyYAML',
            'biplist',
            'python-mimeparse>=0.1.4',
            'nose',
        ),
    )
