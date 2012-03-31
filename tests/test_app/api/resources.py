# If we have from ..documents import * it doesn't work. Anybody knows why?
from test_app.documents import *

from tastypie_mongoengine.resources import MongoEngineResource, MongoEngineListResource
from tastypie_mongoengine.fields import (   EmbeddedDocumentField, 
                                            EmbeddedListField,
                                            EmbeddedSortedListField,
                                        )

from tastypie.authorization import Authorization
from tastypie.fields import ForeignKey

class PersonResource(MongoEngineResource):
    class Meta:
        queryset = Person.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete']
        authorization = Authorization()

class CustomerResource(MongoEngineResource):
    person = ForeignKey(to='test_app.api.resources.PersonResource', attribute='person', full=True)
    
    class Meta:
        queryset = Customer.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete']
        authorization = Authorization()

class EmbededDocumentFieldTestResource(MongoEngineResource):
    customer = EmbeddedDocumentField(embedded='test_app.api.resources.EmbeddedPersonResource', attribute='customer')
                                               
    class Meta:
        queryset = EmbededDocumentFieldTest.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete']
        authorization = Authorization()

class DictFieldTestResource(MongoEngineResource):
    class Meta:
        queryset = DictFieldTest.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete']
        authorization = Authorization()

class ListFieldTestResource(MongoEngineResource):
    class Meta:
        queryset = ListFieldTest.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete']
        authorization = Authorization()


class EmbeddedSortedListFieldTestResource(MongoEngineResource):
    embeddedlist = EmbeddedSortedListField(of='test_app.api.resources.EmbeddedPersonListResource', attribute='embeddedlist', full=True)
    
    class Meta:
        queryset = EmbeddedListFieldTest.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete']
        authorization = Authorization()

class EmbeddedPersonResource(MongoEngineResource):
    class Meta:
        object_class = EmbeddedPerson
        allowed_methods = ['get', 'post', 'put', 'delete']
        authorization = Authorization()

class EmbeddedPersonListResource(EmbeddedPersonResource, MongoEngineListResource):
    pass