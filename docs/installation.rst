Installation
============

Using pip_ simply by doing::

    pip install django-pushserver
    
or by installing from source with::
    
    python setup.py install

.. _pip: http://pypi.python.org/pypi/pip

In your settings.py add ``tastypie`` and ``tastypie_mongoengine`` to ``INSTALLED_APPS``::

    INSTALLED_APPS += (
        'tastypie',
        'tastypie_mongoengine',
    )

You must also establish a connection with mongoengine::

    import mongoengine
    mongoengine.connect('tpme_tests')