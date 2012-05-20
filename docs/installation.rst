Installation
============

Using pip_ simply by doing::

    pip install django-tastypie-mongoengine
    
or by installing from source with::
    
    python setup.py install

.. _pip: http://pypi.python.org/pypi/pip

In your settings.py add ``tastypie`` and ``tastypie_mongoengine`` to ``INSTALLED_APPS``::

    INSTALLED_APPS += (
        'tastypie',
        'tastypie_mongoengine',
    )

You must also `connect MongoEngine`_ to the database::

    MONGO_DATABASE_NAME = 'database'

    import mongoengine
    mongoengine.connect(MONGO_DATABASE_NAME)

.. _connect MongoEngine: http://readthedocs.org/docs/mongoengine-odm/en/latest/django.html
