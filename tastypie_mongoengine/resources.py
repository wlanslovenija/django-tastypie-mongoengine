from django.conf.urls.defaults import url
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from tastypie.resources import ModelResource, ModelDeclarativeMetaclass
from tastypie.http import *
from tastypie.utils import trailing_slash, dict_strip_unicode_keys
from tastypie.exceptions import ImmediateHttpResponse, NotFound
from tastypie.bundle import Bundle
from tastypie import fields as tastypie_fields
#from .fields import EmbeddedCollection

class MongoEngineModelDeclarativeMetaclass(ModelDeclarativeMetaclass):
    def __new__(cls, name, bases, attrs):
        meta = attrs.get('Meta')
        
        if meta:
            if hasattr(meta, 'queryset') and not hasattr(meta, 'object_class'):
                setattr(meta, 'object_class', meta.queryset._document)
                
        new_class = super(ModelDeclarativeMetaclass, cls).__new__(cls, name, bases, attrs)
        include_fields = getattr(new_class._meta, 'fields', [])
        excludes = getattr(new_class._meta, 'excludes', [])
        field_names = new_class.base_fields.keys()

        for field_name in field_names:
            if field_name == 'resource_uri':
                continue
            if field_name in new_class.declared_fields:
                continue
            if len(include_fields) and not field_name in include_fields:
                del(new_class.base_fields[field_name])
            if len(excludes) and field_name in excludes:
                del(new_class.base_fields[field_name])

        # Add in the new fields.
        new_class.base_fields.update(new_class.get_fields(include_fields, excludes))
        
        print new_class.base_fields

        if getattr(new_class._meta, 'include_absolute_url', True):
            if not 'absolute_url' in new_class.base_fields:
                new_class.base_fields['absolute_url'] = fields.CharField(attribute='get_absolute_url', readonly=True)
        elif 'absolute_url' in new_class.base_fields and not 'absolute_url' in attrs:
            del(new_class.base_fields['absolute_url'])

        return new_class

class MongoEngineResource(ModelResource):
    """Minor enhancements to the stock ModelResource to allow subresources."""
    
    __metaclass__ = MongoEngineModelDeclarativeMetaclass
    
    def dispatch_subresource(self, request, subresource_name, **kwargs):
        field = self.fields[subresource_name]
        resource = field.to_class()
        request_type = kwargs.pop('request_type')
        return resource.dispatch(request_type, request, **kwargs)


    def base_urls(self):
        base = super(MongoEngineResource, self).base_urls()

        embedded = ()#((name, obj) for name, obj in self.fields.items() if isinstance(obj, EmbeddedCollection))

        embedded_urls = []

        for name, obj in embedded:
            embedded_urls.extend([
                url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w-]*)/(?P<subresource_name>%s)%s$" %
                    (self._meta.resource_name, name, trailing_slash()),
                    self.wrap_view('dispatch_subresource'),
                    {'request_type': 'list'},
                    name='api_dispatch_subresource_list'),

                url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w-]*)/(?P<subresource_name>%s)/(?P<index>\w[\w-]*)%s$" %
                    (self._meta.resource_name, name, trailing_slash()),
                    self.wrap_view('dispatch_subresource'),
                    {'request_type': 'detail'},
                    name='api_dispatch_subresource_detail')
                ])
        return embedded_urls + base
    
    def get_object_list(self, request):
        """
        An ORM-specific implementation of ``get_object_list``.

        Returns a queryset that may have been limited by other overrides.
        """
        return self._meta.queryset.clone()
    
    @classmethod
    def api_field_from_mongo_field(cls, f, default=tastypie_fields.CharField):
        """
        Returns the field type that would likely be associated with each
        mongoengine type.
        """
        result = default

        if f.__class__.__name__ in ('ComplexDateTimeField', 'DateTimeField'):
            result = tastypie_fields.DateTimeField
        elif f.__class__.__name__ in ('BooleanField',):
            result = tastypie_fields.BooleanField
        elif f.__class__.__name__ in ('FloatField',):
            result = tastypie_fields.FloatField
        elif f.__class__.__name__ in ('DecimalField',):
            result = tastypie_fields.DecimalField
        elif f.__class__.__name__ in ('IntField',):
            result = tastypie_fields.IntegerField
        elif f.__class__.__name__ in ('FileField', 'BinaryField'):
            result = tastypie_fields.FileField

        return result
    
    @classmethod
    def get_fields(cls, fields=None, excludes=None):
        """
        Given any explicit fields to include and fields to exclude, add
        additional fields based on the associated model.
        """
        final_fields = {}
        fields = fields or []
        excludes = excludes or []

        if not cls._meta.object_class:
            return final_fields

        for name, f in cls._meta.object_class._fields.iteritems():
            # If the field name is already present, skip
            if name in cls.base_fields:
                continue

            # If field is not present in explicit field listing, skip
            if fields and name not in fields:
                continue

            # If field is in exclude list, skip
            if excludes and name in excludes:
                continue

            # Might need it in the future
            #if cls.should_skip_field(f):
            #    continue

            api_field_class = cls.api_field_from_mongo_field(f)

            kwargs = {
                'attribute': name,
                'unique':    f.unique,
                'default':   f.default
            }

            if f.required is False:
                kwargs['null'] = True

            final_fields[name] = api_field_class(**kwargs)
            final_fields[name].instance_name = name

        return final_fields