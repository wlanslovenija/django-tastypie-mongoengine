from tastypie_mongoengine.resources import MongoEngineResource

from tastypie.authorization import Authorization

from ..documents import *

class PersonResource(MongoEngineResource):
    class Meta:
        queryset = Person.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete', 'patch']
        authorization = Authorization()

class CustomerResource(MongoEngineResource):
    class Meta:
        queryset = Customer.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete', 'patch']
        authorization = Authorization()

class EmbededDocumentFieldTestResource(MongoEngineResource):
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