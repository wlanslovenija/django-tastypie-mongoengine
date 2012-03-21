from tastypie import fields as tasty_fields
from tastypie.exceptions import ImmediateHttpResponse, NotFound
from tastypie.http import *
from tastypie.resources import Resource, DeclarativeMetaclass
from tastypie.bundle import Bundle

from mongoengine import EmbeddedDocument
from mongoengine import fields as mongo_fields

from . import fields

FIELD_MAP = {
    mongo_fields.BooleanField:  tasty_fields.BooleanField,
    mongo_fields.DateTimeField: tasty_fields.DateTimeField,
    mongo_fields.IntField:      tasty_fields.IntegerField,
    mongo_fields.FloatField:    tasty_fields.FloatField,
    mongo_fields.DictField:     fields.DictField
# Char Fields:
#  StringField, ObjectIdField, EmailField, URLField
# TODO
# 'ReferenceField',
# 'DecimalField', 'GenericReferenceField', 'FileField',
# 'BinaryField', , 'GeoPointField']
}

class DocumentDeclarativeMetaclass(DeclarativeMetaclass):
    def __new__(self, name, bases, attrs):
        meta = attrs.get('Meta')

        if meta:
            if hasattr(meta, 'queryset') and not hasattr(meta, 'object_class'):
                setattr(meta, 'object_class', meta.queryset._document)

            if hasattr(meta, 'object_class') and not hasattr(meta, 'queryset'):
                if hasattr(meta.object_class, 'objects'):
                    setattr(meta, 'queryset', meta.object_class.objects.all())
            
            document_type = getattr(meta, 'object_class')
            
            if issubclass(document_type, EmbeddedDocument):
                if hasattr(meta, 'include_resource_uri'):
                    if getattr(meta, 'include_resource_uri'):
                      raise TastypieError("include_resource_uri cannot be True when the resource is an instance of EmbeddedDocument: %s" % document_type)
                else:
                  setattr(meta, 'include_resource_uri', False)

        new_class = super(DocumentDeclarativeMetaclass, self).__new__(self, name, bases, attrs)
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

        if getattr(new_class._meta, 'include_absolute_url', True):
            if not 'absolute_url' in new_class.base_fields:
                new_class.base_fields['absolute_url'] = fields.CharField(attribute='get_absolute_url', readonly=True)
        elif 'absolute_url' in new_class.base_fields and not 'absolute_url' in attrs:
            del(new_class.base_fields['absolute_url'])

        return new_class

class MongoEngineResource(Resource):
    __metaclass__ = DocumentDeclarativeMetaclass
    
    @classmethod
    def resource_for_document_type(self, document_type):        
        class Meta:
            object_class = document_type

        return DocumentDeclarativeMetaclass('%sResource' % document_type.__name__, (DocumentResource,), {'Meta': Meta})
    
    @classmethod
    def api_field_from_mongoengine_field(self, f, default=tasty_fields.CharField):
        """
        Returns the field type that would likely be associated with each
        mongoengine type.
        """        
        if isinstance(f, mongo_fields.ListField):
            inner_field, field_args = self.api_field_from_mongoengine_field(f.field)
            return fields.ListField, {'inner_field': inner_field(**field_args)}
        elif isinstance(f, mongo_fields.EmbeddedDocumentField):
            return fields.EmbeddedResourceField, {'resource_type': self.resource_for_document_type(f.document_type_obj)}
        else:
            while(f != type):
                if f in FIELD_MAP:
                    return FIELD_MAP[f], { }

                f = f.__class__

        return default, { }
    
    @classmethod
    def get_fields(self, fields=None, excludes=None):
        """
        Given any explicit fields to include and fields to exclude, add
        additional fields based on the associated model.
        """
        final_fields = {}
        fields = fields or []
        excludes = excludes or []
        
        if not self._meta.object_class:
            return final_fields
        
        for name, f in self._meta.object_class._fields.iteritems():
            # If the field name is already present, skip
            if name in self.base_fields:
                continue
            
            # If field is not present in explicit field listing, skip
            if fields and name not in fields:
                continue
            
            # If field is in exclude list, skip
            if excludes and name in excludes:
                continue
            
            api_field_class, kwargs = self.api_field_from_mongoengine_field(f)
            
            kwargs.update({
                'attribute': name,
                'unique':        f.unique,
                'default':     f.default
            })
            
            if f.required is False:
                kwargs['null'] = True
            
            final_fields[name] = api_field_class(**kwargs)
            final_fields[name].instance_name = name

        return final_fields
    
    def get_resource_uri(self, bundle_or_obj):
        kwargs = {
            'resource_name': self._meta.resource_name,
        }

        if isinstance(bundle_or_obj, Bundle):
            kwargs['pk'] = bundle_or_obj.obj.pk
        else:
            kwargs['pk'] = bundle_or_obj.pk

        if self._meta.api_name is not None:
            kwargs['api_name'] = self._meta.api_name

        return self._build_reverse_url("api_dispatch_detail", kwargs=kwargs)
    
    def get_object_list(self, request):
        return self._meta.queryset.clone()

    def obj_get_list(self, request=None, **kwargs):
        # TODO: filters from GET query
        return self.get_object_list(request)
        
    def obj_get(self, request=None, **kwargs):
        return self.get_object_list(request).get(pk=kwargs['pk'])