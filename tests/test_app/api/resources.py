from ..documents import *

from tastypie_mongoengine.resources import MongoEngineResource, MongoEngineListResource
from tastypie_mongoengine.fields import (   ListField, 
                                            DictField, 
                                            EmbeddedDocumentField, 
                                            EmbeddedListField,
                                            EmbeddedCollection,
                                        )

from tastypie.authorization import Authorization
from tastypie.fields import ForeignKey

class PersonResource(MongoEngineResource):
    class Meta:
        queryset = Person.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete', 'patch']
        authorization = Authorization()

class CustomerResource(MongoEngineResource):
    person = ForeignKey(to='test_app.api.resources.PersonResource', attribute='person', full=True)
    
    class Meta:
        queryset = Customer.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete', 'patch']
        authorization = Authorization()

class EmbededDocumentFieldTestResource(MongoEngineResource):
    customer = EmbeddedDocumentField(embedded='test_app.api.resources.PersonResource', attribute='customer')
                                               
    class Meta:
        queryset = EmbededDocumentFieldTest.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete', 'patch']
        authorization = Authorization()

class DictFieldTestResource(MongoEngineResource):
    class Meta:
        queryset = DictFieldTest.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete', 'patch']
        authorization = Authorization()

class ListFieldTestResource(MongoEngineResource):
    class Meta:
        queryset = ListFieldTest.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete', 'patch']
        authorization = Authorization()

class EmbeddedListFieldTestResource(MongoEngineResource):
    class Meta:
        queryset = EmbeddedListFieldTest.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete', 'patch']
        authorization = Authorization()