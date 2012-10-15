from tastypie import authorization as tastypie_authorization, fields as tastypie_fields

from tastypie_mongoengine import fields, paginator, resources

from test_project.test_app import documents

class StrangePersonResource(resources.MongoEngineResource):
    class Meta:
        queryset = documents.StrangePerson.objects.all()
        excludes = ('hidden',)

class OtherStrangePersonResource(resources.MongoEngineResource):
    class Meta:
        queryset = documents.StrangePerson.objects.all()
        excludes = ('hidden',)

class PersonResource(resources.MongoEngineResource):
    class Meta:
        # Ordering by id so that pagination is predictable
        queryset = documents.Person.objects.all().order_by('id')
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()
        ordering = ('name',)
        excludes = ('hidden',)
        paginator_class = paginator.Paginator

        polymorphic = {
            'person': 'self',
            'strangeperson': StrangePersonResource,
        }

class PersonObjectClassResource(resources.MongoEngineResource):
    class Meta:
        object_class = documents.Person
        allowed_methods = ('get', 'post')
        authorization = tastypie_authorization.Authorization()
        resource_name = 'personobjectclass'

class OnlySubtypePersonResource(resources.MongoEngineResource):
    class Meta:
        queryset = documents.Person.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()
        excludes = ('hidden',)

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
        excludes = ('hidden',)

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

class EmbeddedCommentWithIDResource(resources.MongoEngineResource):
    class Meta:
        object_class = documents.EmbeddedCommentWithID
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()
        paginator_class = paginator.Paginator

class DocumentWithIDResource(resources.MongoEngineResource):
    comments = fields.EmbeddedListField(of='test_project.test_app.api.resources.EmbeddedCommentWithIDResource', attribute='comments', full=True, null=True)

    class Meta:
        queryset = documents.DocumentWithID.objects.all()
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
    extra_list = tastypie_fields.ListField()

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

class EmbeddedListFieldNonFullTestResource(resources.MongoEngineResource):
    embeddedlist = fields.EmbeddedListField(of='test_project.test_app.api.resources.EmbeddedPersonResource', attribute='embeddedlist', full=False, null=True)

    class Meta:
        queryset = documents.EmbeddedListFieldTest.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()

class ReferencedListFieldTestResource(resources.MongoEngineResource):
    referencedlist = fields.ReferencedListField(of='test_project.test_app.api.resources.PersonResource', attribute='referencedlist', full=True, null=True)

    class Meta:
        queryset = documents.ReferencedListFieldTest.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()

class ReferencedListFieldNonFullTestResource(resources.MongoEngineResource):
    referencedlist = fields.ReferencedListField(of='test_project.test_app.api.resources.PersonResource', attribute='referencedlist', full=False, null=True)

    class Meta:
        queryset = documents.ReferencedListFieldTest.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()

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

class AutoAllocationFieldTestResource(resources.MongoEngineResource):
    slug = tastypie_fields.CharField(readonly=True, attribute='slug')

    class Meta:
        queryset = documents.AutoAllocationFieldTest.objects.all()
        allowed_methods = ('get', 'post', 'put', 'patch', 'delete')
        authorization = tastypie_authorization.Authorization()
