from builtins import next
from builtins import str
from builtins import object
import itertools
import re
import sys

from django.conf import urls
from django.core import exceptions, urlresolvers
from django.db.models import base as models_base
from future.utils import with_metaclass
try:
    # Before Django 1.8
    from django.utils.datastructures import SortedDict as OrderedDict
except ImportError:
    # After Django 1.8
    from collections import OrderedDict

try:
    # Django 1.5+
    from django.db.models import constants
except ImportError:
    # Before Django 1.5
    from django.db.models.sql import constants

from tastypie import bundle as tastypie_bundle, exceptions as tastypie_exceptions, fields as tastypie_fields, http, resources, utils

import mongoengine
from mongoengine import fields as mongoengine_fields, queryset
from mongoengine.queryset.transform import MATCH_OPERATORS
from tastypie_mongoengine import fields as tastypie_mongoengine_fields

from tastypie.exceptions import NotFound
from django.core.urlresolvers import Resolver404


# When Tastypie accesses query terms used by QuerySet it assumes the interface of Django ORM.
# We use a mock Query object to provide the same interface and return query terms by MongoEngine.
# MongoEngine code might not expose these query terms, so we fallback to hard-coded values.

class Query(object):
    query_terms = set(MATCH_OPERATORS) 

if not hasattr(queryset.QuerySet, 'query'):
    queryset.QuerySet.query = Query()

CONTENT_TYPE_RE = re.compile(r'.*; type=([\w\d-]+);?')


class NOT_HYDRATED(object):
    pass


class ListQuerySet(OrderedDict):
    # Workaround for https://github.com/toastdriven/django-tastypie/pull/670
    query = Query()

    def _process_filter_value(self, value):
        # Sometimes value is passed as a list of one value
        # (if filter was converted from QueryDict, for example)
        if isinstance(value, (list, tuple)):
            assert len(value) == 1
            return value[0]
        else:
            return value

    def filter(self, **kwargs):
        result = self

        # pk optimization
        if 'pk' in kwargs:
            pk = str(self._process_filter_value(kwargs.pop('pk')))
            if pk in result:
                result = ListQuerySet([(str(pk), result[pk])])
            # Sometimes None is passed as a pk to not filter by pk
            elif pk is not None:
                result = ListQuerySet()

        for field, value in kwargs.items():
            value = self._process_filter_value(value)
            if constants.LOOKUP_SEP in field:
                raise tastypie_exceptions.InvalidFilterError("Unsupported filter: (%s, %s)" % (field, value))

            try:
                result = ListQuerySet([(str(obj.pk), obj) for obj in result.values() if getattr(obj, field) == value])
            except AttributeError as ex:
                raise tastypie_exceptions.InvalidFilterError(ex)

        return result

    def attrgetter(self, attr):
        def getter(obj):
            return self.resolve_attr(obj, attr)
        return getter

    def resolve_attr(self, obj, attr):
        for name in attr.split(constants.LOOKUP_SEP):
            while isinstance(obj, list):
                # Try to be a bit similar to MongoDB
                for o in obj:
                    if hasattr(o, name):
                        obj = o
                        break
                else:
                    obj = obj[0]
            obj = getattr(obj, name)
        return obj

    def order_by(self, *field_names):
        if not len(field_names):
            return self

        result = self

        for field in reversed(field_names):
            if field.startswith('-'):
                reverse = True
                field = field[1:]
            else:
                reverse = False

            try:
                result = [(str(obj.pk), obj) for obj in sorted(result, key=self.attrgetter(field), reverse=reverse)]
            except (AttributeError, IndexError) as ex:
                raise tastypie_exceptions.InvalidSortError(ex)

        return ListQuerySet(result)

    def __iter__(self):
        return iter(self.values())

    def __reversed__(self):
        for key in reversed(self.keyOrder):
            yield self[key]

    def __getitem__(self, key):
        # Tastypie access object_list[0], so we pretend to be
        # a list here (order is same as our iteration order)
        if isinstance(key, (int, int)):
            return next(itertools.islice(self, key, key + 1))
        # Tastypie also access sliced object_list in paginator
        elif isinstance(key, slice):
            return itertools.islice(self, key.start, key.stop, key.step)
        else:
            # We could convert silently to unicode here, but it is
            # better to check to find possible errors in program logic
            assert isinstance(key, str), key
            return super(ListQuerySet, self).__getitem__(key)


# Adapted from PEP 257
def trim(docstring):
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return the first paragraph as a single string:
    return '\n'.join(trimmed).split('\n\n')[0]


class MongoEngineModelDeclarativeMetaclass(resources.ModelDeclarativeMetaclass):
    """
    This class has the same functionality as its supper ``ModelDeclarativeMetaclass``.
    Only thing it does differently is how it sets ``object_class`` and ``queryset`` attributes.

    This is an internal class and is not used by the end user of tastypie_mongoengine.
    """

    def __new__(cls, name, bases, attrs):
        meta = attrs.get('Meta')

        if meta:
            if hasattr(meta, 'queryset') and not hasattr(meta, 'object_class'):
                setattr(meta, 'object_class', meta.queryset._document)

            if hasattr(meta, 'object_class') and not hasattr(meta, 'queryset'):
                if hasattr(meta.object_class, 'objects'):
                    setattr(meta, 'queryset', meta.object_class.objects.all())
                elif issubclass(meta.object_class, mongoengine.EmbeddedDocument):
                    # Workaround for https://github.com/toastdriven/django-tastypie/pull/670
                    # We ignore queryset value later on, so we can set it here to empty one
                    setattr(meta, 'queryset', ListQuerySet())

        new_class = super(resources.ModelDeclarativeMetaclass, cls).__new__(cls, name, bases, attrs)
        include_fields = getattr(new_class._meta, 'fields', [])
        excludes = getattr(new_class._meta, 'excludes', [])

        field_names = list(new_class.base_fields.keys())

        for field_name in field_names:
            if field_name == 'resource_uri':
                if hasattr(new_class, '_parent'):
                    if new_class._parent._meta.object_class and issubclass(new_class._parent._meta.object_class, mongoengine.EmbeddedDocument):
                        # TODO: We do not support yet nested resources
                        # If parent is embedded document, then also this one do not have its own resource_uri
                        del(new_class.base_fields[field_name])
                elif new_class._meta.object_class and issubclass(new_class._meta.object_class, mongoengine.EmbeddedDocument):
                    # Embedded documents which are not in lists (do not have _parent) do not have their own resource_uri
                    del(new_class.base_fields[field_name])
            if field_name in new_class.declared_fields:
                continue
            if len(include_fields) and field_name not in include_fields:
                del(new_class.base_fields[field_name])
            if len(excludes) and field_name in excludes:
                del(new_class.base_fields[field_name])

        # Add in the new fields
        new_class.base_fields.update(new_class.get_fields(include_fields, excludes))

        if getattr(new_class._meta, 'include_absolute_url', True):
            if 'absolute_url' not in new_class.base_fields:
                new_class.base_fields['absolute_url'] = tastypie_fields.CharField(attribute='get_absolute_url', readonly=True)
        elif 'absolute_url' in new_class.base_fields and 'absolute_url' not in attrs:
            del(new_class.base_fields['absolute_url'])

        type_map = getattr(new_class._meta, 'polymorphic', {})

        if type_map and getattr(new_class._meta, 'include_resource_type', True):
            if 'resource_type' not in new_class.base_fields:
                new_class.base_fields['resource_type'] = tastypie_fields.CharField(readonly=True)
        elif 'resource_type' in new_class.base_fields and 'resource_type' not in attrs:
            del(new_class.base_fields['resource_type'])

        seen_types = set()
        for typ, resource in type_map.items():
            if resource == 'self':
                type_map[typ] = new_class
                break
            # In the code for polymorphic resources we are assuming
            # that document classes are not duplicated among used resources
            # (that each resource is linked to its own document class)
            # So we are checking this assumption here
            if type_map[typ]._meta.object_class in seen_types:
                raise exceptions.ImproperlyConfigured("Used polymorphic resources should each use its own document class.")
            else:
                seen_types.add(type_map[typ]._meta.object_class)

        if new_class._meta.object_class:
            # In MongoEngine 0.7.6+ embedded documents do not have exceptions anymore,
            # but this prevents are from reusing existing Tastypie code

            exceptions_to_merge = [exc for exc in (queryset.DoesNotExist, queryset.MultipleObjectsReturned) if not hasattr(new_class._meta.object_class, exc.__name__)]
            module = new_class._meta.object_class.__module__
            for exc in exceptions_to_merge:
                name = exc.__name__
                parents = tuple(getattr(base, name) for base in new_class._meta.object_class._get_bases(bases) if hasattr(base, name)) or (exc,)
                # Create new exception and set to new_class
                exception = type(name, parents, {'__module__': module})
                setattr(new_class._meta.object_class, name, exception)

        return new_class


class MongoEngineResource(with_metaclass(MongoEngineModelDeclarativeMetaclass, resources.ModelResource)):
    """
    Adaptation of ``ModelResource`` to MongoEngine.
    """

    def get_via_uri(self, uri, request=None):
        """
        This pulls apart the salient bits of the URI and populates the
        resource via a ``obj_get``.

        Optionally accepts a ``request``.

        If you need custom behavior based on other portions of the URI,
        simply override this method.
        """
        try:
            return super(MongoEngineResource, self).get_via_uri(uri, request)
        except (NotFound, Resolver404):
            # if this is a polymorphic resource check the uri against the resources in self._meta.polymorphic
            type_map = getattr(self._meta, 'polymorphic', {})
            for type_, resource in type_map.items():
                try:
                    return resource().get_via_uri(uri, request)
                except (NotFound, Resolver404):
                    pass
            # the uri wasn't found at any of the polymorphic resources, it is an incorrect URI for this resource
            raise
        except Exception as e:
            raise e

    # Data preparation.

    def dispatch_subresource(self, request, subresource_name, **kwargs):
        field = self.fields[subresource_name]
        resource = field.to_class(self._meta.api_name)
        return resource.dispatch(request=request, **kwargs)

    def base_urls(self):
        base = super(MongoEngineResource, self).base_urls()

        embedded_urls = []
        embedded = (name for name, obj in self.fields.items() if isinstance(obj, tastypie_mongoengine_fields.EmbeddedListField))

        for name in embedded:
            embedded_urls.extend((
                urls.url(
                    r"^(?P<resource_name>%s)/(?P<pk>\w[\w-]*)/(?P<subresource_name>%s)%s$" % (self._meta.resource_name, name, utils.trailing_slash()),
                    self.wrap_view('dispatch_subresource'),
                    {'request_type': 'list'},
                    name='api_dispatch_subresource_list',
                ),
                urls.url(
                    r"^(?P<resource_name>%s)/(?P<pk>\w[\w-]*)/(?P<subresource_name>%s)/(?P<subresource_pk>\w[\w-]*)%s$" % (self._meta.resource_name, name, utils.trailing_slash()),
                    self.wrap_view('dispatch_subresource'),
                    {'request_type': 'detail'},
                    name='api_dispatch_subresource_detail',
                ),
            ))

        return embedded_urls + base

    def _reset_collection(self):
        """
        Because MongoEngine creates collection connection when queryset object is initialized,
        we have to make sure that currently configured connection to database is really used.
        This happens for example in tests, where querysets are initialized as resource classes
        are imported, but then database connection is changed to test database.
        """

        self._meta.queryset._document._collection = None
        self._meta.queryset._collection_obj = self._meta.queryset._document._get_collection()
        if hasattr(self._meta.queryset, '_reset_already_indexed'):
            self._meta.queryset._reset_already_indexed()

    def get_object_list(self, request):
        """
        An ORM-specific implementation of ``get_object_list``.
        Returns a queryset that may have been limited by other overrides.
        """

        self._reset_collection()
        return self._meta.queryset.clone()

    def _get_object_type(self, request):
        match = CONTENT_TYPE_RE.match(request.META.get('CONTENT_TYPE', ''))
        if match:
            return match.group(1)
        elif 'type' in request.GET:
            return request.GET.get('type')
        else:
            return None

    def _wrap_polymorphic(self, resource, fun):
        object_class = self._meta.object_class
        qs = self._meta.queryset
        resource_name = self._meta.resource_name
        base_fields = self.base_fields
        fields = self.fields
        try:
            self._meta.object_class = resource._meta.object_class
            self._meta.queryset = resource._meta.queryset
            self.base_fields = resource.base_fields.copy()
            self.fields = resource.fields.copy()
            if getattr(self._meta, 'prefer_polymorphic_resource_uri', False):
                if resource.get_resource_uri():
                    self._meta.resource_name = resource._meta.resource_name
            if getattr(self._meta, 'include_resource_type', True):
                self.base_fields['resource_type'] = base_fields['resource_type']
                self.fields['resource_type'] = fields['resource_type']
            return fun()
        finally:
            self._meta.object_class = object_class
            self._meta.queryset = qs
            self._meta.resource_name = resource_name
            self.base_fields = base_fields
            self.fields = fields

    def _wrap_request(self, request, fun):
        type_map = getattr(self._meta, 'polymorphic', {})
        if not type_map:
            return fun()

        object_type = self._get_object_type(request)
        if not object_type:
            # Polymorphic resources are enabled, but
            # nothing is passed, so set it to a default
            try:
                object_type = self._get_type_from_class(type_map, self._meta.object_class)
            except KeyError:
                raise tastypie_exceptions.BadRequest("Invalid object type.")

        if object_type not in type_map:
            raise tastypie_exceptions.BadRequest("Invalid object type.")

        resource = type_map[object_type](self._meta.api_name)

        # Optimization
        if resource._meta.object_class is self._meta.object_class:
            return fun()

        return self._wrap_polymorphic(resource, fun)

    def dispatch(self, request_type, request, **kwargs):
        # We process specially only requests with payload
        if 'HTTP_X_HTTP_METHOD_OVERRIDE' in request.META:
            the_method = request.META['HTTP_X_HTTP_METHOD_OVERRIDE'].lower()
            if the_method == 'delete':
                return super(MongoEngineResource, self).dispatch(request_type, request, **kwargs)
        else:
            the_method = request.method.lower()

        if not request.body:
            assert the_method not in ('put', 'post', 'patch'), the_method
            return super(MongoEngineResource, self).dispatch(request_type, request, **kwargs)

        assert the_method in ('put', 'post', 'patch'), the_method + ":" + request.body

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

    def full_dehydrate(self, bundle, for_list=False):
        type_map = getattr(self._meta, 'polymorphic', {})
        if not type_map:
            return super(MongoEngineResource, self).full_dehydrate(bundle, for_list)

        # Optimization
        if self._meta.object_class is bundle.obj.__class__:
            return super(MongoEngineResource, self).full_dehydrate(bundle, for_list)

        resource = self._get_resource_from_class(type_map, bundle.obj.__class__)(self._meta.api_name)
        return self._wrap_polymorphic(resource, lambda: super(MongoEngineResource, self).full_dehydrate(bundle, for_list))

    def full_hydrate(self, bundle):
        # When updating objects, we want to force only updates of the same type, and object
        # should be completely replaced if type is changed, so we throw and exception here
        # to direct program logic flow (it is cached and replace instead of update is tried)
        if bundle.obj and self._meta.object_class is not bundle.obj.__class__:
            raise tastypie_exceptions.NotFound("A document instance matching the provided arguments could not be found.")

        bundle = super(MongoEngineResource, self).full_hydrate(bundle)

        # We redo check for required fields as Tastypie is not
        # reliable as it does checks in an inconsistent way
        # (https://github.com/toastdriven/django-tastypie/issues/491)
        for field_object in self.fields.values():
            if field_object.readonly or getattr(field_object, '_primary_key', False):
                continue

            if not field_object.attribute:
                continue

            # Tastypie also skips setting value if it is None, but this means
            # updates to None are ignored: this is not good as it hides invalid
            # PUT/PATCH REST requests (setting value to None which should fail
            # validation (field required) is simply ignored and value is left
            # as it is)
            # (https://github.com/toastdriven/django-tastypie/issues/492)
            # We hydrate field again only if existing value is not None
            if getattr(bundle.obj, field_object.attribute, None) is not None:
                value = NOT_HYDRATED

                # Tastypie also ignores missing fields in PUT,
                # so we check for missing field here
                # (https://github.com/toastdriven/django-tastypie/issues/496)
                if field_object.instance_name not in bundle.data:
                    if field_object.has_default():
                        if callable(field_object.default):
                            value = field_object.default()
                        else:
                            value = field_object.default
                    # If it can be blank, we leave the field as it is, it was possibly already populated or it is not even necessary to be
                    elif field_object.blank:
                        pass
                    else:
                        value = None
                else:
                    value = field_object.hydrate(bundle)
                if value is None:
                    setattr(bundle.obj, field_object.attribute, None)

            if field_object.blank or field_object.null:
                continue

            # We are just trying to fix Tastypie here, for other "null" values
            # like [] and {} we leave to MongoEngine validate to catch them
            if getattr(bundle.obj, field_object.attribute, None) is None:
                raise tastypie_exceptions.ApiFieldError("The '%s' field has no data and doesn't allow a default or null value." % field_object.instance_name)

        return bundle

    def build_schema(self):
        data = super(MongoEngineResource, self).build_schema()

        for field_name, field_object in list(self.fields.items()):
            # We process ListField specially here (and not use field's
            # build_schema) so that Tastypie's ListField can be used
            if isinstance(field_object, tastypie_fields.ListField):
                if getattr(field_object, 'field', None):
                    data['fields'][field_name]['content'] = {}

                    field_type = field_object.field.__class__.__name__.lower()
                    if field_type.endswith('field'):
                        field_type = field_type[:-5]
                    data['fields'][field_name]['content']['type'] = field_type

                    if field_object.field.__doc__:
                        data['fields'][field_name]['content']['help_text'] = trim(field_object.field.__doc__)

            if hasattr(field_object, 'build_schema'):
                data['fields'][field_name].update(field_object.build_schema())

        type_map = getattr(self._meta, 'polymorphic', {})
        if not type_map:
            return data

        data.update({
            'resource_types': list(type_map.keys()),
        })

        return data

    def obj_get(self, bundle, **kwargs):
        # MongoEngine exceptions are separate from Django exceptions, we combine them here
        try:
            return super(MongoEngineResource, self).obj_get(bundle=bundle, **kwargs)
        except self._meta.object_class.DoesNotExist as ex:
            exp = models_base.subclass_exception('DoesNotExist', (self._meta.object_class.DoesNotExist, exceptions.ObjectDoesNotExist), self._meta.object_class.DoesNotExist.__module__)
            raise exp(*ex.args)
        except queryset.DoesNotExist as ex:
            exp = models_base.subclass_exception('DoesNotExist', (queryset.DoesNotExist, exceptions.ObjectDoesNotExist), queryset.DoesNotExist.__module__)
            raise exp(*ex.args)
        except self._meta.object_class.MultipleObjectsReturned as ex:
            exp = models_base.subclass_exception('MultipleObjectsReturned', (self._meta.object_class.MultipleObjectsReturned, exceptions.MultipleObjectsReturned), self._meta.object_class.MultipleObjectsReturned.__module__)
            raise exp(*ex.args)
        except queryset.MultipleObjectsReturned as ex:
            exp = models_base.subclass_exception('MultipleObjectsReturned', (queryset.MultipleObjectsReturned, exceptions.MultipleObjectsReturned), queryset.MultipleObjectsReturned.__module__)
            raise exp(*ex.args)
        except mongoengine.ValidationError as ex:
            exp = models_base.subclass_exception('DoesNotExist', (queryset.DoesNotExist, exceptions.ObjectDoesNotExist), queryset.DoesNotExist.__module__)
            raise exp(*ex.args)

    def obj_create(self, bundle, **kwargs):
        self._reset_collection()
        return super(MongoEngineResource, self).obj_create(bundle, **kwargs)

    # TODO: Use skip_errors?
    def obj_update(self, bundle, skip_errors=False, **kwargs):
        self._reset_collection()

        if not bundle.obj or not getattr(bundle.obj, 'pk', None):
            try:
                bundle.obj = self.obj_get(bundle=bundle, **kwargs)
            except (queryset.DoesNotExist, exceptions.ObjectDoesNotExist):
                raise tastypie_exceptions.NotFound("A document instance matching the provided arguments could not be found.")

        self.authorized_update_detail(self.get_object_list(bundle.request), bundle)
        bundle = self.full_hydrate(bundle)
        return self.save(bundle, skip_errors=skip_errors)

    def obj_delete(self, bundle, **kwargs):
        self._reset_collection()

        # MongoEngine exceptions are separate from Django exceptions and Tastypie
        # expects Django exceptions, so we catch it here ourselves and raise NotFound
        try:
            return super(MongoEngineResource, self).obj_delete(bundle, **kwargs)
        except queryset.DoesNotExist:
            raise tastypie_exceptions.NotFound("A document instance matching the provided arguments could not be found.")

    def create_identifier(self, obj):
        return str(obj.pk)

    def save(self, bundle, skip_errors=False):
        try:
            return super(MongoEngineResource, self).save(bundle, skip_errors)
        except mongoengine.ValidationError as ex:
            raise exceptions.ValidationError(ex.message)

    def save_m2m(self, bundle):
        # Our related documents are not stored in a queryset, but a list,
        # so we have to manually build a list, set it, and save

        for field_name, field_object in list(self.fields.items()):
            if not getattr(field_object, 'is_m2m', False):
                continue

            if not field_object.attribute:
                continue

            if field_object.readonly:
                continue

            related_objs = []

            for related_bundle in bundle.data[field_name]:
                related_bundle.obj.save()
                related_objs.append(related_bundle.obj)

            setattr(bundle.obj, field_object.attribute, related_objs)
            bundle.obj.save()

    @classmethod
    def api_field_from_mongo_field(cls, f, default=tastypie_fields.CharField):
        """
        Returns the field type that would likely be associated with each
        MongoEngine type.
        """

        result = default

        if isinstance(f, (mongoengine.ComplexDateTimeField, mongoengine.DateTimeField)):
            result = tastypie_fields.DateTimeField
        elif isinstance(f, mongoengine.BooleanField):
            result = tastypie_fields.BooleanField
        elif isinstance(f, mongoengine.FloatField):
            result = tastypie_fields.FloatField
        elif isinstance(f, mongoengine.DecimalField):
            result = tastypie_fields.DecimalField
        elif isinstance(f, mongoengine.IntField):
            result = tastypie_fields.IntegerField
        elif isinstance(f, (mongoengine.FileField, mongoengine.BinaryField)):
            result = tastypie_fields.FileField
        elif isinstance(f, mongoengine.DictField):
            result = tastypie_fields.DictField
        elif isinstance(f, mongoengine.ListField):
            result = tastypie_fields.ListField
        elif isinstance(f, mongoengine.GeoPointField):
            result = tastypie_fields.ListField
        elif isinstance(f, mongoengine.ObjectIdField):
            result = tastypie_mongoengine_fields.ObjectId

        return result

    @classmethod
    def api_field_options(cls, name, field, options):
        """
        Allows dynamic change of field options when creating resource
        fields from document fields automatically.
        """

        return options

    @classmethod
    def get_fields(cls, fields=None, excludes=None):
        """
        Given any explicit fields to include and fields to exclude, add
        additional fields based on the associated document.
        """

        final_fields = {}
        fields = fields or []
        excludes = excludes or []

        if not cls._meta.object_class:
            return final_fields

        for name, f in cls._meta.object_class._fields.items():
            # If the field name is already present, skip
            if name in cls.base_fields:
                continue

            # If field is not present in explicit field listing, skip
            if fields and name not in fields:
                continue

            # If field is in exclude list, skip
            if excludes and name in excludes:
                continue

            # TODO: Might need it in the future
            # if cls.should_skip_field(f):
            #     continue

            api_field_class = cls.api_field_from_mongo_field(f)

            primary_key = f.primary_key or name == getattr(cls._meta, 'id_field', 'id')

            kwargs = {
                'attribute': name,
                'unique': f.unique or primary_key,
                'null': not f.required and not primary_key,
                'help_text': getattr(f, 'help_text', None),
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

            kwargs = cls.api_field_options(name, f, kwargs)

            final_fields[name] = api_field_class(**kwargs)
            final_fields[name].instance_name = name
            final_fields[name]._primary_key = primary_key

            # We store MongoEngine field so that schema output can show
            # to which content the list is limited to (if any)
            if isinstance(f, mongoengine.ListField):
                final_fields[name].field = f.field

        return final_fields

    def update_in_place(self, request, original_bundle, new_data):
        """
        Update the object in original_bundle in-place using new_data.
        """

        # TODO: Is this the place to use MongoDB atomic operations to update the document?

        from tastypie.utils import dict_strip_unicode_keys
        original_bundle.data.update(**dict_strip_unicode_keys(new_data))

        # Now we've got a bundle with the new data sitting in it and we're
        # we're basically in the same spot as a PUT request. So the rest of this
        # function is cribbed from put_detail.
        self.alter_deserialized_detail_data(request, original_bundle.data)

        # Removed request from kwargs, breaking obj_get filter, currently present
        # in tastypie. See https://github.com/toastdriven/django-tastypie/issues/824.
        kwargs = {
            self._meta.detail_uri_name: self.get_bundle_detail_data(original_bundle),
        }
        return self.obj_update(bundle=original_bundle, **kwargs)


class MongoEngineListResource(MongoEngineResource):
    """
    A MongoEngine resource used in conjunction with EmbeddedListField.
    """

    def __init__(self, api_name=None):
        super(MongoEngineListResource, self).__init__(api_name)

        self.instance = None
        self.parent = self._parent(api_name)

        # Validate the fields and set primary key if needed
        for field_name, field in self._meta.object_class._fields.items():
            if field.primary_key:
                # Ensure only one primary key is set
                current_pk = getattr(self._meta, 'id_field', None)
                if current_pk and current_pk != field_name:
                    raise ValueError('Cannot override primary key field')

                # Set primary key
                if not current_pk:
                    self._meta.id_field = field_name

    def _safe_get(self, bundle, **kwargs):
        filters = self.remove_api_resource_names(kwargs)

        try:
            return self.parent.cached_obj_get(bundle=bundle, **filters)
        except (queryset.DoesNotExist, exceptions.ObjectDoesNotExist):
            raise tastypie_exceptions.ImmediateHttpResponse(response=http.HttpNotFound())

    def dispatch(self, request_type, request, **kwargs):
        subresource_pk = kwargs.pop('subresource_pk', None)

        bundle = self.build_bundle(request=request)
        self.instance = self._safe_get(bundle, **kwargs)

        # We use subresource pk as pk from now on
        kwargs['pk'] = subresource_pk

        return super(MongoEngineListResource, self).dispatch(request_type, request, **kwargs)

    def remove_api_resource_names(self, url_dict):
        kwargs_subset = super(MongoEngineListResource, self).remove_api_resource_names(url_dict)

        for key in ['subresource_name']:
            try:
                del(kwargs_subset[key])
            except KeyError:
                pass

        return kwargs_subset

    def get_object_list(self, request):
        if not self.instance:
            return ListQuerySet()

        pk_field = getattr(self._meta, 'id_field', None)

        if pk_field is not None:
            object_list = []
            for obj in getattr(self.instance, self.attribute):
                pk = getattr(obj, pk_field)
                obj.__class__.pk = tastypie_mongoengine_fields.link_property(pk_field)
                object_list.append((str(pk), obj))
            return ListQuerySet(object_list)

        else:
            def add_index(index, obj):
                obj.pk = index
                return obj

            return ListQuerySet([(str(index), add_index(index, obj)) for index, obj in enumerate(getattr(self.instance, self.attribute))])

    def obj_create(self, bundle, **kwargs):
        try:
            bundle.obj = self._meta.object_class()

            for key, value in list(kwargs.items()):
                setattr(bundle.obj, key, value)

            bundle = self.full_hydrate(bundle)

            object_list = getattr(self.instance, self.attribute)
            pk_field = getattr(self._meta, 'id_field', None)

            if pk_field is None:
                bundle.obj.pk = len(object_list)
            else:
                bundle.obj.__class__.pk = tastypie_mongoengine_fields.link_property(pk_field)

            object_list.append(bundle.obj)

            self.save_related(bundle)

            self.instance.save()

            m2m_bundle = self.hydrate_m2m(bundle)
            self.save_m2m(m2m_bundle)
            return bundle
        except mongoengine.ValidationError as ex:
            raise exceptions.ValidationError(ex.message)

    def find_embedded_document(self, objects, pk_field, pk):
        # TODO: Would it be faster to traverse in reversed direction? Because probably last elements are fetched more often in practice?
        # TODO: Should we cache information about mappings between IDs and elements?
        for i, obj in enumerate(objects):
            if getattr(obj, pk_field) == pk:
                return i

        raise IndexError("Embedded document with primary key '%s' not found." % pk)

    # TODO: Use skip_errors?
    def obj_update(self, bundle, skip_errors=False, **kwargs):
        try:
            if not bundle.obj or not getattr(bundle.obj, 'pk', None):
                try:
                    bundle.obj = self.obj_get(bundle=bundle, **kwargs)
                except (queryset.DoesNotExist, exceptions.ObjectDoesNotExist):
                    raise tastypie_exceptions.NotFound("A document instance matching the provided arguments could not be found.")

            bundle = self.full_hydrate(bundle)

            object_list = getattr(self.instance, self.attribute)
            pk_field = getattr(self._meta, 'id_field', None)

            if pk_field is None:
                object_list[bundle.obj.pk] = bundle.obj
            else:
                object_list[self.find_embedded_document(object_list, pk_field, bundle.obj.pk)] = bundle.obj

            self.save_related(bundle)

            self.instance.save()

            m2m_bundle = self.hydrate_m2m(bundle)
            self.save_m2m(m2m_bundle)
            return bundle
        except mongoengine.ValidationError as ex:
            raise exceptions.ValidationError(ex.message)

    def obj_delete(self, bundle, **kwargs):
        obj = kwargs.pop('_obj', None)

        if not getattr(obj, 'pk', None):
            try:
                obj = self.obj_get(bundle=bundle, **kwargs)
            except (queryset.DoesNotExist, exceptions.ObjectDoesNotExist):
                raise tastypie_exceptions.NotFound("A document instance matching the provided arguments could not be found.")

        object_list = getattr(self.instance, self.attribute)
        pk_field = getattr(self._meta, 'id_field', None)

        if pk_field is None:
            object_list.pop(obj.pk)
        else:
            object_list.pop(self.find_embedded_document(object_list, pk_field, obj.pk))

        # Make sure to delete FileField files
        for fieldname, field in list(obj._fields.items()):
            if isinstance(field, mongoengine_fields.FileField):
                obj[fieldname].delete()

        self.instance.save()

    def detail_uri_kwargs(self, bundle_or_obj):
        if isinstance(bundle_or_obj, tastypie_bundle.Bundle):
            obj = bundle_or_obj.obj
        else:
            obj = bundle_or_obj

        kwargs = {
            'resource_name': self.parent._meta.resource_name,
            'subresource_name': self.attribute,
            'subresource_pk': obj.pk,
        }

        if hasattr(obj, 'parent'):
            # pk could not exist in the case of nested resources, but we should not come here in this
            # case as we should remove resource_uri from fields in MongoEngineModelDeclarativeMetaclass
            # TODO: Support nested resources
            kwargs['pk'] = obj.parent.pk
        else:
            kwargs['pk'] = self.instance.pk

        if self._meta.api_name is not None:
            kwargs['api_name'] = self._meta.api_name

        return kwargs

    def get_resource_uri(self, bundle_or_obj=None, url_name='api_dispatch_subresource_list'):
        if bundle_or_obj is not None:
            url_name = 'api_dispatch_subresource_detail'

        try:
            return self._build_reverse_url(url_name, kwargs=self.resource_uri_kwargs(bundle_or_obj))
        except urlresolvers.NoReverseMatch:
            return ''
