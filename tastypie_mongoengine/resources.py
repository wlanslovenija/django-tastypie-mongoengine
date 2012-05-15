import re

from django.conf.urls.defaults import url
from django.core import exceptions
from django.db.models import base

from tastypie import bundle as tastypie_bundle, exceptions as tastypie_exceptions, fields as tastypie_fields, http, resources, utils

import mongoengine
from mongoengine import queryset

from tastypie_mongoengine import fields

CONTENT_TYPE_RE = re.compile('.*; type=([\w\d-]+);?')

class MongoEngineModelDeclarativeMetaclass(resources.ModelDeclarativeMetaclass):
    """
    This class has the same functionality as its supper ``ModelDeclarativeMetaclass``.
    Only thing it does diffrently is how it sets ``object_class`` and ``queryset`` attributes.

    This is an internal class and is not used by the end user of tastypie_mongoengine.
    """

    def __new__(self, name, bases, attrs):
        meta = attrs.get('Meta')

        if meta:
            if hasattr(meta, 'queryset') and not hasattr(meta, 'object_class'):
                setattr(meta, 'object_class', meta.queryset._document)

            if hasattr(meta, 'object_class') and not hasattr(meta, 'queryset'):
                if hasattr(meta.object_class, 'objects'):
                    setattr(meta, 'queryset', meta.object_class.objects.all())

        new_class = super(resources.ModelDeclarativeMetaclass, self).__new__(self, name, bases, attrs)
        include_fields = getattr(new_class._meta, 'fields', [])
        excludes = getattr(new_class._meta, 'excludes', [])
        field_names = new_class.base_fields.keys()

        for field_name in field_names:
            if field_name == 'resource_uri':
                # Delete resource_uri from fields if this is mongoengine.EmbeddedDocument
                if meta and issubclass(meta.object_class, mongoengine.EmbeddedDocument):
                    del(new_class.base_fields[field_name])
            if field_name in new_class.declared_fields:
                continue
            if len(include_fields) and not field_name in include_fields:
                del(new_class.base_fields[field_name])
            if len(excludes) and field_name in excludes:
                del(new_class.base_fields[field_name])

        # Add in the new fields
        new_class.base_fields.update(new_class.get_fields(include_fields, excludes))

        if getattr(new_class._meta, 'include_absolute_url', True):
            if not 'absolute_url' in new_class.base_fields:
                new_class.base_fields['absolute_url'] = tastypie_fields.CharField(attribute='get_absolute_url', readonly=True)
        elif 'absolute_url' in new_class.base_fields and not 'absolute_url' in attrs:
            del(new_class.base_fields['absolute_url'])

        type_map = getattr(new_class._meta, 'polymorphic', {})

        if type_map and getattr(new_class._meta, 'include_resource_type', True):
            if not 'resource_type' in new_class.base_fields:
                new_class.base_fields['resource_type'] = tastypie_fields.CharField(readonly=True)
        elif 'resource_type' in new_class.base_fields and not 'resource_type' in attrs:
            del(new_class.base_fields['resource_type'])

        for typ, resource in type_map.items():
            if resource == 'self':
                type_map[typ] = new_class
                break

        return new_class

class MongoEngineResource(resources.ModelResource):
    """
    Minor enhancements to the stock ``ModelResource`` to allow subresources.
    """

    __metaclass__ = MongoEngineModelDeclarativeMetaclass

    def dispatch_subresource(self, request, subresource_name, **kwargs):
        field = self.fields[subresource_name]
        resource = field.to_class()
        request_type = kwargs.pop('request_type')
        return resource.dispatch(request_type, request, **kwargs)

    def base_urls(self):
        base = super(MongoEngineResource, self).base_urls()

        embedded = ((name, obj) for name, obj in self.fields.items() if isinstance(obj, fields.EmbeddedSortedListField))

        embedded_urls = []

        for name, obj in embedded:
            embedded_urls.extend([
                url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w-]*)/(?P<subresource_name>%s)%s$" % (self._meta.resource_name, name, utils.trailing_slash()),
                    self.wrap_view('dispatch_subresource'),
                    {'request_type': 'list'},
                    name='api_dispatch_subresource_list',
                ),

                url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w-]*)/(?P<subresource_name>%s)/(?P<index>\w[\w-]*)%s$" % (self._meta.resource_name, name, utils.trailing_slash()),
                    self.wrap_view('dispatch_subresource'),
                    {'request_type': 'detail'},
                    name='api_dispatch_subresource_detail',
                ),
            ])
        return embedded_urls + base

    def get_object_list(self, request):
        """
        An ORM-specific implementation of ``get_object_list``.
        Returns a queryset that may have been limited by other overrides.
        """

        return self._meta.queryset.clone()

    def _get_object_type(self, request):
        match = CONTENT_TYPE_RE.match(request.META.get('CONTENT_TYPE', ''))
        if match:
            return match.group(1)
        else:
            return None

    def _wrap_polymorphic(self, resource, fun):
        object_class = self._meta.object_class
        queryset = self._meta.queryset
        base_fields = self.base_fields
        fields = self.fields
        try:
            self._meta.object_class = resource._meta.object_class
            self._meta.queryset = resource._meta.queryset
            self.base_fields = resource.base_fields.copy()
            self.fields = resource.fields.copy()
            if getattr(self._meta, 'include_resource_type', True):
                self.base_fields['resource_type'] = base_fields['resource_type']
                self.fields['resource_type'] = fields['resource_type']
            return fun()
        finally:
            self._meta.object_class = object_class
            self._meta.queryset = queryset
            self.base_fields = base_fields
            self.fields = fields

    def _wrap_request(self, request, fun):
        type_map = getattr(self._meta, 'polymorphic', {})
        if not type_map:
            return fun()

        object_type = self._get_object_type(request)
        if not object_type:
            return fun()

        if object_type not in type_map:
            raise tastypie_exceptions.BadRequest("Invalid object type.")

        resource = type_map[object_type]

        # Optimization
        if resource._meta.object_class is self._meta.object_class:
            return fun()

        return self._wrap_polymorphic(resource, fun)

    def dispatch(self, request_type, request, **kwargs):
        # We process specially only requests with payload
        if not request.body:
            assert request.method.lower() not in ('put', 'post', 'patch'), request.method
            return super(MongoEngineResource, self).dispatch(request_type, request, **kwargs)

        assert request.method.lower() in ('put', 'post', 'patch'), request.method

        return self._wrap_request(request, lambda: super(MongoEngineResource, self).dispatch(request_type, request, **kwargs))

    def get_schema(self, request, **kwargs):
        return self._wrap_request(request, lambda: super(MongoEngineResource, self).get_schema(request, **kwargs))

    def _get_resource_from_class(self, type_map, cls):
        for resource in type_map.values():
            if resource._meta.object_class is cls:
                return resource
        raise KeyError(cls)

    def _get_type_from_class(self, type_map, cls):
        # As we are overriding self._meta.object_class we have to make sure
        # that we do not miss real match, so if self._meta.object_class
        # matches, we still check other items, otherwise we return immediately
        res = None
        for typ, resource in type_map.items():
            if resource._meta.object_class is cls:
                if resource._meta.object_class is self._meta.object_class:
                    res = typ
                else:
                    return typ
        if res is not None:
            return res
        else:
            raise KeyError(cls)

    def dehydrate_resource_type(self, bundle):
        type_map = getattr(self._meta, 'polymorphic', {})
        if not type_map:
            return None

        return self._get_type_from_class(type_map, bundle.obj.__class__)

    def full_dehydrate(self, bundle):
        type_map = getattr(self._meta, 'polymorphic', {})
        if not type_map:
            return super(MongoEngineResource, self).full_dehydrate(bundle)

        # Optimization
        if self._meta.object_class is bundle.obj.__class__:
            return super(MongoEngineResource, self).full_dehydrate(bundle)

        resource = self._get_resource_from_class(type_map, bundle.obj.__class__)
        return self._wrap_polymorphic(resource, lambda: super(MongoEngineResource, self).full_dehydrate(bundle))

    def full_hydrate(self, bundle):
        # When updating objects, we want to force only updates of the same type, and object
        # should be completely replaced if type is changed, so we throw and exception here
        # to direct program logic flow (it is catched and replace instead of update is tried)
        if bundle.obj and self._meta.object_class is not bundle.obj.__class__:
            raise tastypie_exceptions.NotFound("A model instance matching the provided arguments could not be found.")

        bundle = super(MongoEngineResource, self).full_hydrate(bundle)

        # We redo check for required fields as Tastypie is not reliable here
        for field_object in self.fields.values():
            if field_object.null or field_object.readonly:
                continue

            if not field_object.attribute:
                continue

            if isinstance(field_object, mongoengine.ListField):
                if not getattr(bundle.obj, field_object.attribute, []): # None, False are also not good
                    raise tastypie_exceptions.ApiFieldError("The '%s' field has no data and doesn't allow a default or null value." % field_object.instance_name)
            elif isinstance(field_object, mongoengine.DictField):
                if not getattr(bundle.obj, field_object.attribute, {}): # None, False are also not good
                    raise tastypie_exceptions.ApiFieldError("The '%s' field has no data and doesn't allow a default or null value." % field_object.instance_name)
            else:
                if getattr(bundle.obj, field_object.attribute, None) is None: # False could be good
                    raise tastypie_exceptions.ApiFieldError("The '%s' field has no data and doesn't allow a default or null value." % field_object.instance_name)

        return bundle

    def build_schema(self):
        data = super(MongoEngineResource, self).build_schema()

        type_map = getattr(self._meta, 'polymorphic', {})
        if not type_map:
            return data

        data.update({
            'resource_types': type_map.keys(),
        })

        return data

    def obj_get(self, request=None, **kwargs):
        # MongoEngine exceptions are separate from Django excpetions, we combine them here
        try:
            return super(MongoEngineResource, self).obj_get(request, **kwargs)
        except self._meta.object_class.DoesNotExist, e:
            exp = base.subclass_exception('DoesNotExist', (self._meta.object_class.DoesNotExist, exceptions.ObjectDoesNotExist), self._meta.object_class.DoesNotExist.__module__)
            raise exp(*e.args)
        except queryset.DoesNotExist, e:
            exp = base.subclass_exception('DoesNotExist', (queryset.DoesNotExist, exceptions.ObjectDoesNotExist), queryset.DoesNotExist.__module__)
            raise exp(*e.args)
        except self._meta.object_class.MultipleObjectsReturned, e:
            exp = base.subclass_exception('MultipleObjectsReturned', (self._meta.object_class.MultipleObjectsReturned, exceptions.MultipleObjectsReturned), self._meta.object_class.MultipleObjectsReturned.__module__)
            raise exp(*e.args)
        except queryset.MultipleObjectsReturned, e:
            exp = base.subclass_exception('MultipleObjectsReturned', (queryset.MultipleObjectsReturned, exceptions.MultipleObjectsReturned), queryset.MultipleObjectsReturned.__module__)
            raise exp(*e.args)

    @classmethod
    def api_field_from_mongo_field(cls, f, default=tastypie_fields.CharField):
        """
        Returns the field type that would likely be associated with each
        MongoEngine type.
        """

        result = default

        # TODO: This should probably be changed to a series of isinstance calls
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
        elif f.__class__.__name__ in ('DictField',):
            result = tastypie_fields.DictField
        elif f.__class__.__name__ in ('ListField',):
            result = tastypie_fields.ListField
        elif f.__class__.__name__ in ('GeoPointField',):
            result = tastypie_fields.ListField
        elif f.__class__.__name__ in ('ObjectIdField',):
            result = fields.ObjectId

        return result

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

            # TODO: Might need it in the future
            #if cls.should_skip_field(f):
            #    continue

            api_field_class = self.api_field_from_mongo_field(f)

            kwargs = {
                'attribute': name,
                'unique': f.unique,
                'null': not f.required,
                'help_text': f.help_text,
            }

            # If field is not required, it does not matter if set default value,
            # so we do
            if not f.required:
                kwargs['default'] = f.default
            else:
                # MongoEngine does not really differ between user-specified default
                # and its default, so we try to guess
                if isinstance(f, mongoengine.ListField):
                    if not callable(f.default) or f.default() != []: # If not MongoEngine's default
                        kwargs['default'] = f.default
                elif isinstance(f, mongoengine.DictField):
                    if not callable(f.default) or f.default() != {}: # If not MongoEngine's default
                        kwargs['default'] = f.default
                else:
                    if f.default is not None: # If not MongoEngine's default
                        kwargs['default'] = f.default

            final_fields[name] = api_field_class(**kwargs)
            final_fields[name].instance_name = name

            # TODO: What about MongoEngine custom validation methods for fields?

        return final_fields

class MongoEngineListResource(MongoEngineResource):
    """
    An embedded MongoDB list acting as a collection. Used in conjunction with
    EmbeddedListField or EmbeddedSortedListField.
    """

    def base_urls(self):
        return super(MongoEngineResource, self).base_urls()

    def dispatch_subresource(self, request, subresource_name, **kwargs):
        return super(MongoEngineResource, self).dispatch_subresource(request, subresource_name, **kwargs)

    def __init__(self, parent=None, attribute=None, api_name=None):
        self.parent = parent
        self.attribute = attribute
        self.instance = None

        super(MongoEngineListResource, self).__init__(api_name)

    def dispatch(self, request_type, request, **kwargs):
        self.instance = self.safe_get(request, **kwargs)

        return super(MongoEngineListResource, self).dispatch(request_type, request, **kwargs)

    def safe_get(self, request, **kwargs):
        filters = self.remove_api_resource_names(kwargs)
        try:
            del(filters['index'])
        except KeyError:
            pass

        try:
            return self.parent.cached_obj_get(request=request, **filters)
        except exceptions.ObjectDoesNotExist:
            raise tastypie_exceptions.ImmediateHttpResponse(response=http.HttpGone())

    def remove_api_resource_names(self, url_dict):
        kwargs_subset = url_dict.copy()

        for key in ['api_name', 'resource_name', 'subresource_name']:
            try:
                del(kwargs_subset[key])
            except KeyError:
                pass

        return kwargs_subset

    def get_object_list(self, request):
        if not self.instance:
            return []

        def add_index(index, obj):
            obj.pk = index
            return obj

        return [add_index(index, obj) for index, obj in enumerate(getattr(self.instance, self.attribute))]

    def obj_get_list(self, request=None, **kwargs):
        return self.get_object_list(request)

    def obj_get(self, request=None, **kwargs):
        index = int(kwargs['index'])
        try:
            return self.get_object_list(request)[index]
        except IndexError:
            raise tastypie_exceptions.ImmediateHttpResponse(response=http.HttpGone())

    def obj_create(self, bundle, request=None, **kwargs):
        bundle = self.full_hydrate(bundle)
        getattr(self.instance, self.attribute).append(bundle.obj)
        self.instance.save()
        return bundle

    def obj_update(self, bundle, request=None, **kwargs):
        if hasattr(kwargs, 'index'):
            index = int(kwargs['index'])
        else:
            index = 0

        try:
            bundle.obj = self.get_object_list(request)[index]
        except IndexError:
            raise tastypie_exceptions.NotFound("A model instance matching the provided arguments could not be found.")
        bundle = self.full_hydrate(bundle)
        new_index = int(bundle.data['id'])
        lst = getattr(self.instance, self.attribute)
        lst.pop(index)
        lst.insert(new_index, bundle.obj)
        self.instance.save()
        return bundle

    def obj_delete(self, request=None, **kwargs):
        index = int(kwargs['index'])
        self.obj_get(request, **kwargs)
        getattr(self.instance, self.attribute).pop(index)
        self.instance.save()

    def obj_delete_list(self, request=None, **kwargs):
        setattr(self.instance, self.attribute, [])
        self.instance.save()

    def put_detail(self, request, **kwargs):
        """
        Either updates an existing resource or creates a new one with the
        provided data.

        Calls ``obj_update`` with the provided data first, but falls back to
        ``obj_create`` if the object does not already exist.

        If a new resource is created, return ``HttpCreated`` (201 Created).
        If an existing resource is modified, return ``HttpAccepted`` (204 No Content).
        """

        deserialized = self.deserialize(request, request.raw_post_data, format=request.META.get('CONTENT_TYPE', 'application/json'))
        bundle = self.build_bundle(data=utils.dict_strip_unicode_keys(deserialized))
        self.is_valid(bundle, request)

        try:
            updated_bundle = self.obj_update(bundle, request=request, **kwargs)
            return http.HttpAccepted()
        except:
            updated_bundle = self.obj_create(bundle, request=request, **kwargs)
            return http.HttpCreated(location=self.get_resource_uri(updated_bundle))

    def get_resource_uri(self, bundle_or_obj):
        if isinstance(bundle_or_obj, tastypie_bundle.Bundle):
            obj = bundle_or_obj.obj
        else:
            obj = bundle_or_obj

        kwargs = {
            'resource_name': self.parent._meta.resource_name,
            'subresource_name': self.attribute,
        }

        if hasattr(obj, 'parent'):
            kwargs['pk'] = obj.parent._id
        else:
            kwargs['pk'] = self.instance.id

        kwargs['index'] = obj.pk

        if self._meta.api_name is not None:
            kwargs['api_name'] = self._meta.api_name

        ret = self._build_reverse_url('api_dispatch_subresource_detail', kwargs=kwargs)

        return ret
