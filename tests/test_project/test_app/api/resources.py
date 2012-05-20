from tastypie import authorization, fields as tastypie_fields

from tastypie_mongoengine import resources, fields

from test_project.test_app import documents

class StrangePersonResource(resources.MongoEngineResource):
    class Meta:
        queryset = documents.StrangePerson.objects.all()

class PersonResource(resources.MongoEngineResource):
    class Meta:
        queryset = documents.Person.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = authorization.Authorization()

        polymorphic = {
            'person': 'self',
            'strangeperson': StrangePersonResource,
        }

class EmbeddedStrangePersonResource(resources.MongoEngineResource):
    class Meta:
        object_class = documents.EmbeddedStrangePerson

class EmbeddedPersonResource(resources.MongoEngineResource):
    class Meta:
        object_class = documents.EmbeddedPerson
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = authorization.Authorization()

        polymorphic = {
            'person': 'self',
            'strangeperson': EmbeddedStrangePersonResource,
        }

class CustomerResource(resources.MongoEngineResource):
    person = fields.ReferenceField(to='test_project.test_app.api.resources.PersonResource', attribute='person', full=True)

    class Meta:
        queryset = documents.Customer.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = authorization.Authorization()

class EmbeddedDocumentFieldTestResource(resources.MongoEngineResource):
    customer = fields.EmbeddedDocumentField(embedded='test_project.test_app.api.resources.EmbeddedPersonResource', attribute='customer')

    class Meta:
        queryset = documents.EmbeddedDocumentFieldTest.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = authorization.Authorization()

class DictFieldTestResource(resources.MongoEngineResource):
    class Meta:
        queryset = documents.DictFieldTest.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = authorization.Authorization()

class ListFieldTestResource(resources.MongoEngineResource):
    class Meta:
        queryset = documents.ListFieldTest.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = authorization.Authorization()

class EmbeddedListFieldTestResource(resources.MongoEngineResource):
    embeddedlist = fields.EmbeddedListField(of='test_project.test_app.api.resources.EmbeddedPersonResource', attribute='embeddedlist', full=True)

    class Meta:
        queryset = documents.EmbeddedListFieldTest.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = authorization.Authorization()
