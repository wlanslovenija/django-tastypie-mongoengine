=====
Usage
=====

Usage for simple cases is very similar as with django-tastypie. You should read their tutorial_ first.

.. _tutorial: http://django-tastypie.readthedocs.org/en/latest/tutorial.html

Only difference is when you are defining API resource files.
There you must use ``MongoEngineResource`` instead of ``ModelResource``.

Simple Example
==============

::

    from tastypie import authorization
    from tastypie_mongoengine import resources
    from test_app import documents
    
    class PersonResource(resources.MongoEngineResource):
        class Meta:
            queryset = documents.Person.objects.all()
            allowed_methods = ('get', 'post', 'put', 'delete')
            authorization = authorization.Authorization()
            
EmbeddedDocument
================

When you are using ``EmbeddedDocument`` in your MongoEngine documents, you must define ``object_class``
in Meta class of your resource declaration instead of queryset::

    class EmbeddedPersonResource(resources.MongoEngineResource):
        class Meta:
            object_class = documents.EmbeddedPerson
            ...
    
When you are using normal MongoEngine ``Document`` you can use ``queryset`` or ``object_class``.

Related and Embedded Fields
===========================

All related fields you want exposed through API must be manually defined.

ForeignKey
----------

::

    from tastypie import fields as tastypie_fields
    
    class CustomerResource(resources.MongoEngineResource):
        person = tastypie_fields.ForeignKey(to='test_app.api.resources.PersonResource', attribute='person', full=True)
        ...

EmbeddedDocumentField
---------------------

Embeds a resource inside another resource just like you would in MongoEngine::

    from tastypie_mongoengine import fields

    class EmbeddedDocumentFieldTestResource(resources.MongoEngineResource):
        customer = fields.EmbeddedDocumentField(embedded='test_app.api.resources.EmbeddedPersonResource', attribute='customer')
        ...

MongoEngineListResource
=======================

This resource is used instead of ``MongoEngineResource`` when you want an editable list of embedded documents.
It is used in conjunction with ``EmbeddedSortedListField`` or ``EmbeddedListField``.

::

    class EmbeddedPersonListResource(resources.MongoEngineListResource):
        class Meta:
            object_class = documents.EmbeddedPerson
            ...
            
    class EmbeddedSortedListFieldTestResource(resources.MongoEngineResource):
        embeddedlist = fields.EmbeddedSortedListField(of='test_app.api.resources.EmbeddedPersonListResource', attribute='embeddedlist', full=True)
        ...
