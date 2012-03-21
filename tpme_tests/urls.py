from django.conf.urls.defaults import patterns, include, url

from tastypie.api import Api

from test_app.api.resources import *

v1_api = Api(api_name='v1')
v1_api.register(PersonResource())

urlpatterns = patterns('',
    (r'^api/', include(v1_api.urls)),
)
