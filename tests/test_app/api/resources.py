from test_app import documents

from tastypie_mongoengine import resources
from tastypie_mongoengine import fields

from tastypie import authorization
from tastypie import fields as tastypie_fields

class PersonResource(resources.MongoEngineResource):
    class Meta:
        queryset = documents.Person.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete']
        authorization = authorization.Authorization()

class CustomerResource(resources.MongoEngineResource):
    person = tastypie_fields.ForeignKey(to='test_app.api.resources.PersonResource', attribute='person', full=True)
    
    class Meta:
        queryset = documents.Customer.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete']
        authorization = authorization.Authorization()

class EmbededDocumentFieldTestResource(resources.MongoEngineResource):
    customer = fields.EmbeddedDocumentField(embedded='test_app.api.resources.EmbeddedPersonResource', attribute='customer')
                                               
    class Meta:
        queryset = documents.EmbededDocumentFieldTest.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete']
        authorization = authorization.Authorization()

class DictFieldTestResource(resources.MongoEngineResource):
    class Meta:
        queryset = documents.DictFieldTest.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete']
        authorization = authorization.Authorization()

class ListFieldTestResource(resources.MongoEngineResource):
    class Meta:
        queryset = documents.ListFieldTest.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete']
        authorization = authorization.Authorization()

class EmbeddedSortedListFieldTestResource(resources.MongoEngineResource):
    embeddedlist = fields.EmbeddedSortedListField(of='test_app.api.resources.EmbeddedPersonListResource', attribute='embeddedlist', full=True)
    
    class Meta:
        queryset = documents.EmbeddedListFieldTest.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete']
        authorization = authorization.Authorization()

class EmbeddedPersonResource(resources.MongoEngineResource):
    class Meta:
        object_class = documents.EmbeddedPerson
        allowed_methods = ['get', 'post', 'put', 'delete']
        authorization = authorization.Authorization()

class EmbeddedPersonListResource(EmbeddedPersonResource, resources.MongoEngineListResource):
    pass