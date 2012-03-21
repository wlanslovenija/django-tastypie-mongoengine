from tastypie_mongoengine.resources import MongoEngineResource
from ..documents import *

class PersonResource(MongoEngineResource):
    class Meta:
        queryset = Person.objects.all()
        allowed_methods = ['get']