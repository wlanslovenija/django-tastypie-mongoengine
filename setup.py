import os

from setuptools import setup, find_packages

VERSION = '0.1'

if __name__ == '__main__':
    setup(
        name = 'django-tastypie-mongoengine',
        version = VERSION,
        description = "This is an extension of django-tastypie to support mongoengine.",
        long_description = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read(),
        author = 'Matevz',
        author_email = 'matevz.mihalic@gmail.com',
        url = 'https://github.com/mitar/django-tastypie-mongoengine',
        keywords = "REST RESTful tastypie mongo mongodb mongoengine django",
        license = 'AGPLv3',
        packages = find_packages(),
        classifiers = [
            'Development Status :: 4 - Beta',
            'Environment :: Web Environment',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: GNU Affero General Public License v3',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Framework :: Django',
        ],
        zip_safe = False,
        install_requires = [
            'Django>=1.3',
            'django-tastypie>=0.9.11',
            'mongoengine>=0.6.3',
        ],
    )