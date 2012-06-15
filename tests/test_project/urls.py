from django.conf.urls import patterns, include, url

from tastypie import api

from test_project.test_app.api import resources

v1_api = api.Api(api_name='v1')
v1_api.register(resources.PersonResource())
v1_api.register(resources.OnlySubtypePersonResource())
v1_api.register(resources.CustomerResource())
v1_api.register(resources.BoardResource())
v1_api.register(resources.EmbeddedListInEmbeddedDocTestResource())
v1_api.register(resources.EmbeddedDocumentFieldTestResource())
v1_api.register(resources.DictFieldTestResource())
v1_api.register(resources.ListFieldTestResource())
v1_api.register(resources.EmbeddedListFieldTestResource())
v1_api.register(resources.BooleanMapTestResource())
v1_api.register(resources.EmbeddedListWithFlagFieldTestResource())

urlpatterns = patterns('',
    url(r'^api/', include(v1_api.urls)),
)
