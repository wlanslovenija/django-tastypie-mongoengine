from tastypie import authorization as tastypie_authorization, fields as tastypie_fields

from tastypie_mongoengine import fields, paginator, resources

from test_project.test_app import documents

class StrangePersonResource(resources.MongoEngineResource):
    class Meta:
        queryset = documents.StrangePerson.objects.all()

class OtherStrangePersonResource(resources.MongoEngineResource):
    class Meta:
        queryset = documents.StrangePerson.objects.all()

class PersonResource(resources.MongoEngineResource):
    class Meta:
        # Ordering by id so that pagination is predictable
        queryset = documents.Person.objects.all().order_by('id')
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()
        ordering = ('name',)
        paginator_class = paginator.Paginator

        polymorphic = {
            'person': 'self',
            'strangeperson': StrangePersonResource,
        }

class OnlySubtypePersonResource(resources.MongoEngineResource):
    class Meta:
        queryset = documents.Person.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()

        polymorphic = {
            'strangeperson': StrangePersonResource,
        }

class EmbeddedStrangePersonResource(resources.MongoEngineResource):
    class Meta:
        object_class = documents.EmbeddedStrangePerson

class EmbeddedPersonResource(resources.MongoEngineResource):
    class Meta:
        object_class = documents.EmbeddedPerson
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()
        ordering = ('name',)

        polymorphic = {
            'person': 'self',
            'strangeperson': EmbeddedStrangePersonResource,
        }

class CustomerResource(resources.MongoEngineResource):
    person = fields.ReferenceField(to='test_project.test_app.api.resources.PersonResource', attribute='person', full=True)

    class Meta:
        queryset = documents.Customer.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()

class EmbeddedCommentResource(resources.MongoEngineResource):
    class Meta:
        object_class = documents.EmbeddedComment

class EmbeddedPostResource(resources.MongoEngineResource):
    comments = fields.EmbeddedListField(of='test_project.test_app.api.resources.EmbeddedCommentResource', attribute='comments', full=True, null=True)

    class Meta:
        object_class = documents.EmbeddedPost
        ordering = ('title', 'comments')

class BoardResource(resources.MongoEngineResource):
    posts = fields.EmbeddedListField(of='test_project.test_app.api.resources.EmbeddedPostResource', attribute='posts', full=True, null=True)

    class Meta:
        queryset = documents.Board.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()

class EmbeddedListInEmbeddedDocTestResource(resources.MongoEngineResource):
    post = fields.EmbeddedDocumentField(embedded='test_project.test_app.api.resources.EmbeddedPostResource', attribute='post')

    class Meta:
        queryset = documents.EmbeddedListInEmbeddedDocTest.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()

class EmbeddedDocumentFieldTestResource(resources.MongoEngineResource):
    customer = fields.EmbeddedDocumentField(embedded='test_project.test_app.api.resources.EmbeddedPersonResource', attribute='customer', null=True)

    class Meta:
        queryset = documents.EmbeddedDocumentFieldTest.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()

class DictFieldTestResource(resources.MongoEngineResource):
    class Meta:
        queryset = documents.DictFieldTest.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()

class ListFieldTestResource(resources.MongoEngineResource):
    class Meta:
        queryset = documents.ListFieldTest.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()

class EmbeddedListFieldTestResource(resources.MongoEngineResource):
    embeddedlist = fields.EmbeddedListField(of='test_project.test_app.api.resources.EmbeddedPersonResource', attribute='embeddedlist', full=True, null=True)

    class Meta:
        queryset = documents.EmbeddedListFieldTest.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()
        ordering = ('id', 'embeddedlist')

class BooleanMapTestResource(resources.MongoEngineResource):
    is_published_defined = tastypie_fields.BooleanField(default=False, null=False, attribute='is_published_defined')

    class Meta:
        queryset = documents.BooleanMapTest.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()

class EmbeddedListWithFlagFieldTestResource(resources.MongoEngineResource):
    embeddedlist = fields.EmbeddedListField(of='test_project.test_app.api.resources.EmbeddedPersonResource', attribute='embeddedlist', full=True, null=True)

    class Meta:
        queryset = documents.EmbeddedListWithFlagFieldTest.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()
