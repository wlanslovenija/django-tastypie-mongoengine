from tastypie_mongoengine.resources import MongoEngineResource

from tastypie.authorization import Authorization

from ..documents import *

class PersonResource(MongoEngineResource):
    class Meta:
        queryset = Person.objects.all()
        allowed_methods = ['get', 'post', 'put', 'delete', 'patch']
        authorization = Authorization()