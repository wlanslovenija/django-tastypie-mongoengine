import itertools, re, sys

from django.conf import urls
from django.core import exceptions
from django.db.models import base as models_base
from django.db.models.sql import constants
from django.utils import datastructures

from tastypie import bundle as tastypie_bundle, exceptions as tastypie_exceptions, fields as tastypie_fields, http, resources, utils

import mongoengine
from mongoengine import queryset

import bson

from tastypie_mongoengine import fields

# When Tastypie accesses query terms used by QuerySet it assumes the interface of Django ORM. 
# We use a mock Query object to provide the same interface and return query terms by MongoEngine. 
# MongoEngine code might not expose these query terms, so we fallback to hard-coded values.

QUERY_TERMS_ALL = getattr(queryset, 'QUERY_TERMS_ALL', ('ne', 'gt', 'gte', 'lt', 'lte', 'in', 'nin', 'mod', 'all', 'size', 'exists', 'not', 'within_distance', 'within_spherical_distance', 'within_box', 'within_polygon', 'near', 'near_sphere','contains', 'icontains', 'startswith', 'istartswith', 'endswith', 'iendswith', 'exact', 'iexact', 'match'))

class Query(object):
    query_terms = dict([(query_term, None) for query_term in QUERY_TERMS_ALL])

queryset.QuerySet.query = Query()

CONTENT_TYPE_RE = re.compile('.*; type=([\w\d-]+);?')

class NOT_HYDRATED:
    pass

class ListQuerySet(datastructures.SortedDict):
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
            pk = self._process_filter_value(kwargs.pop('pk'))
            if pk in result:
                result = ListQuerySet([(pk, result[pk])])
            # Sometimes None is passed as a pk to not filter by pk
            elif pk is not None:
                result = ListQuerySet()

        for field, value in kwargs.iteritems():
            value = self._process_filter_value(value)
            if constants.LOOKUP_SEP in field:
                raise tastypie_exceptions.InvalidFilterError("Unsupported filter: (%s, %s)" % (field, value))

            try:
                result = ListQuerySet([(obj.pk, obj) for obj in result.itervalues() if getattr(obj, field) == value])
            except AttributeError, e:
                raise tastypie_exceptions.InvalidFilterError(e)

        return result

    def attrgetter(self, attr):
        def g(obj):
            return self.resolve_attr(obj, attr)
        return g

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
                result = [(obj.pk, obj) for obj in sorted(result, key=self.attrgetter(field), reverse=reverse)]
            except (AttributeError, IndexError), e:
                raise tastypie_exceptions.InvalidSortError(e)

        return ListQuerySet(result)

    def __iter__(self):
        return self.itervalues()

    def __getitem__(self, key):
        # Tastypie access object_list[0], so we pretend to be
        # a list here (order is same as our iteration order)
        if isinstance(key, (int, long)):
            return itertools.islice(self, key, key+1).next()
        # Tastypie also access sliced object_list in paginator
        elif isinstance(key, slice):
            return itertools.islice(self, key.start, key.stop, key.step)
        else:
            return super(ListQuerySet, self).__getitem__(key)

# Adapted from PEP 257
def trim(docstring):
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxint
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxint:
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

        seen_types = set()
        for typ, resource in type_map.iteritems():
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

        return new_class

class MongoEngineResource(resources.ModelResource):
    """
    Adaptation of ``ModelResource`` to MongoEngine.
    """

    __metaclass__ = MongoEngineModelDeclarativeMetaclass

    def dispatch_subresource(self, request, subresource_name, **kwargs):
        field = self.fields[subresource_name]
        resource = field.to_class(self._meta.api_name)
        return resource.dispatch(request=request, **kwargs)

    def base_urls(self):
        base = super(MongoEngineResource, self).base_urls()

        embedded_urls = []
        embedded = ((name, obj) for name, obj in self.fields.iteritems() if isinstance(obj, fields.EmbeddedListField))

        for name, obj in embedded:
            embedded_urls.extend((
                urls.url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w-]*)/(?P<subresource_name>%s)%s$" % (self._meta.resource_name, name, utils.trailing_slash()),
                    self.wrap_view('dispatch_subresource'),
                    {'request_type': 'list'},
                    name='api_dispatch_subresource_list',
                ),
                urls.url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w-]*)/(?P<subresource_name>%s)/(?P<index>\d+)%s$" % (self._meta.resource_name, name, utils.trailing_slash()),
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
            self._meta.queryset = qs
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
        if not request.body:
            assert request.method.lower() not in ('put', 'post', 'patch'), request.method
            return super(MongoEngineResource, self).dispatch(request_type, request, **kwargs)

        assert request.method.lower() in ('put', 'post', 'patch'), request.method

        return self._wrap_request(request, lambda: super(MongoEngineResource, self).dispatch(request_type, request, **kwargs))

    def get_schema(self, request, **kwargs):
        return self._wrap_request(request, lambda: super(MongoEngineResource, self).get_schema(request, **kwargs))

    def _get_resource_from_class(self, type_map, cls):
        for resource in type_map.itervalues():
            if resource._meta.object_class is cls:
                return resource
        raise KeyError(cls)

    def _get_type_from_class(self, type_map, cls):
        # As we are overriding self._meta.object_class we have to make sure
        # that we do not miss real match, so if self._meta.object_class
        # matches, we still check other items, otherwise we return immediately
        res = None
        for typ, resource in type_map.iteritems():
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

        resource = self._get_resource_from_class(type_map, bundle.obj.__class__)(self._meta.api_name)
        return self._wrap_polymorphic(resource, lambda: super(MongoEngineResource, self).full_dehydrate(bundle))

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
        for field_object in self.fields.itervalues():
            if field_object.readonly:
                continue

            if not field_object.attribute:
                continue

            value = NOT_HYDRATED

            # Tastypie also skips setting value if it is None, but this means
            # updates to None are ignored: this is not good as it hides invalid
            # PUT/PATCH REST requests (setting value to None which should fail
            # validation (field required) is simply ignored and value is left
            # as it is)
            # (https://github.com/toastdriven/django-tastypie/issues/492)
            # We hydrate field again only if existing value is not None
            if getattr(bundle.obj, field_object.attribute, None) is not None:
                # Tastypie also ignores missing fields in PUT,
                # so we check for missing field here
                # (https://github.com/toastdriven/django-tastypie/issues/496)
                if field_object.instance_name not in bundle.data:
                    if field_object._default is not tastypie_fields.NOT_PROVIDED:
                        if callable(field_object.default):
                            value = field_object.default()
                        else:
                            value = field_object.default
                    else:
                        value = None
                else:
                    value = field_object.hydrate(bundle)
                if value is None:
                    # This does not really set None in a way that calling
                    # getattr on bundle.obj would return None later on
                    # This is how MongoEngine is implemented
                    # (https://github.com/hmarr/mongoengine/issues/505)
                    setattr(bundle.obj, field_object.attribute, None)

            if field_object.blank or field_object.null:
                continue

            # We are just trying to fix Tastypie here, for other "null" values
            # like [] and {} we leave to validate bellow to catch them
            if getattr(bundle.obj, field_object.attribute, None) is None or value is None: # We also have to check value, read comment above
                raise tastypie_exceptions.ApiFieldError("The '%s' field has no data and doesn't allow a default or null value." % field_object.instance_name)

        # We validate MongoEngine object here so that possible exception
        # is thrown before going to MongoEngine layer, wrapped in
        # Django exception so that it is handled properly
        # is_valid method is too early as bundle.obj is not yet ready then
        try:
            # Validation fails for unsaved related resources, so
            # we fake pk here temporary, for validation code to
            # assume resource is saved
            pk = getattr(bundle.obj, 'pk', None)
            try:
                if pk is None:
                    bundle.obj.pk = bson.ObjectId()
                bundle.obj.validate()
            finally:
                if pk is None:
                    bundle.obj.pk = pk
        except mongoengine.ValidationError, e:
            raise exceptions.ValidationError(e.message)

        return bundle

    def build_schema(self):
        data = super(MongoEngineResource, self).build_schema()

        for field_name, field_object in self.fields.items():
            # We process ListField specially here (and not use field's
            # build_schema) so that Tastypie's ListField can be used
            if isinstance(field_object, tastypie_fields.ListField):
                if field_object.field:
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
            'resource_types': type_map.keys(),
        })

        return data

    def obj_get(self, request=None, **kwargs):
        # MongoEngine exceptions are separate from Django exceptions, we combine them here
        try:
            return super(MongoEngineResource, self).obj_get(request, **kwargs)
        except self._meta.object_class.DoesNotExist, e:
            exp = models_base.subclass_exception('DoesNotExist', (self._meta.object_class.DoesNotExist, exceptions.ObjectDoesNotExist), self._meta.object_class.DoesNotExist.__module__)
            raise exp(*e.args)
        except queryset.DoesNotExist, e:
            exp = models_base.subclass_exception('DoesNotExist', (queryset.DoesNotExist, exceptions.ObjectDoesNotExist), queryset.DoesNotExist.__module__)
            raise exp(*e.args)
        except self._meta.object_class.MultipleObjectsReturned, e:
            exp = models_base.subclass_exception('MultipleObjectsReturned', (self._meta.object_class.MultipleObjectsReturned, exceptions.MultipleObjectsReturned), self._meta.object_class.MultipleObjectsReturned.__module__)
            raise exp(*e.args)
        except queryset.MultipleObjectsReturned, e:
            exp = models_base.subclass_exception('MultipleObjectsReturned', (queryset.MultipleObjectsReturned, exceptions.MultipleObjectsReturned), queryset.MultipleObjectsReturned.__module__)
            raise exp(*e.args)
        except mongoengine.ValidationError, e:
            exp = models_base.subclass_exception('DoesNotExist', (queryset.DoesNotExist, exceptions.ObjectDoesNotExist), queryset.DoesNotExist.__module__)
            raise exp(*e.args)

    def obj_create(self, bundle, request=None, **kwargs):
        self._reset_collection()
        return super(MongoEngineResource, self).obj_create(bundle, request, **kwargs)

    def obj_update(self, bundle, request=None, **kwargs):
        self._reset_collection()

        if not bundle.obj or not getattr(bundle.obj, 'pk', None):
            try:
                bundle.obj = self.obj_get(request, **kwargs)
            except (queryset.DoesNotExist, exceptions.ObjectDoesNotExist):
                raise tastypie_exceptions.NotFound("A document instance matching the provided arguments could not be found.")

        bundle = self.full_hydrate(bundle)

        self.save_related(bundle)

        bundle.obj.save()

        m2m_bundle = self.hydrate_m2m(bundle)
        self.save_m2m(m2m_bundle)
        return bundle

    def obj_delete(self, request=None, **kwargs):
        self._reset_collection()

        # MongoEngine exceptions are separate from Django exceptions and Tastypie
        # expects Django exceptions, so we catch it here ourselves and raise NotFound
        try:
            return super(MongoEngineResource, self).obj_delete(request, **kwargs)
        except queryset.DoesNotExist:
            raise tastypie_exceptions.NotFound("A document instance matching the provided arguments could not be found.")

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
            result = fields.ObjectId

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

            # TODO: Might need it in the future
            #if cls.should_skip_field(f):
            #    continue

            api_field_class = cls.api_field_from_mongo_field(f)

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

            kwargs = cls.api_field_options(name, f, kwargs)

            final_fields[name] = api_field_class(**kwargs)
            final_fields[name].instance_name = name

            # We store MongoEngine field so that schema output can show
            # to which content the list is limited to (if any)
            if isinstance(f, mongoengine.ListField):
                final_fields[name].field = f.field

        return final_fields

class MongoEngineListResource(MongoEngineResource):
    """
    A MongoEngine resource used in conjunction with EmbeddedListField.
    """

    def __init__(self, api_name=None):
        super(MongoEngineListResource, self).__init__(api_name)

        self.instance = None
        self.parent = self._parent(api_name)

    def _safe_get(self, request, **kwargs):
        filters = self.remove_api_resource_names(kwargs)

        try:
            return self.parent.cached_obj_get(request=request, **filters)
        except (queryset.DoesNotExist, exceptions.ObjectDoesNotExist):
            raise tastypie_exceptions.ImmediateHttpResponse(response=http.HttpNotFound())

    def dispatch(self, request_type, request, **kwargs):
        index = None
        if 'index' in kwargs:
            index = kwargs.pop('index')

        self.instance = self._safe_get(request, **kwargs)

        # We use pk as index from now on
        kwargs['pk'] = index

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

        def add_index(index, obj):
            obj.pk = unicode(index)
            return obj

        return ListQuerySet([(unicode(index), add_index(index, obj)) for index, obj in enumerate(getattr(self.instance, self.attribute))])

    def obj_create(self, bundle, request=None, **kwargs):
        bundle.obj = self._meta.object_class()

        for key, value in kwargs.items():
            setattr(bundle.obj, key, value)

        bundle = self.full_hydrate(bundle)

        object_list = getattr(self.instance, self.attribute)
        object_list.append(bundle.obj)

        bundle.obj.pk = unicode(len(object_list) - 1)

        self.save_related(bundle)

        self.instance.save()

        m2m_bundle = self.hydrate_m2m(bundle)
        self.save_m2m(m2m_bundle)
        return bundle

    def obj_update(self, bundle, request=None, **kwargs):
        if not bundle.obj or not getattr(bundle.obj, 'pk', None):
            try:
                bundle.obj = self.obj_get(request, **kwargs)
            except (queryset.DoesNotExist, exceptions.ObjectDoesNotExist):
                raise tastypie_exceptions.NotFound("A document instance matching the provided arguments could not be found.")

        bundle = self.full_hydrate(bundle)

        object_list = getattr(self.instance, self.attribute)
        object_list[int(bundle.obj.pk)] = bundle.obj

        self.save_related(bundle)

        self.instance.save()

        m2m_bundle = self.hydrate_m2m(bundle)
        self.save_m2m(m2m_bundle)
        return bundle

    def obj_delete(self, request=None, **kwargs):
        obj = kwargs.pop('_obj', None)

        if not getattr(obj, 'pk', None):
            try:
                obj = self.obj_get(request, **kwargs)
            except (queryset.DoesNotExist, exceptions.ObjectDoesNotExist):
                raise exceptions.NotFound("A document instance matching the provided arguments could not be found.")

        getattr(self.instance, self.attribute).pop(int(obj.pk))
        self.instance.save()

    def get_resource_uri(self, bundle_or_obj):
        if isinstance(bundle_or_obj, tastypie_bundle.Bundle):
            obj = bundle_or_obj.obj
        else:
            obj = bundle_or_obj

        kwargs = {
            'resource_name': self.parent._meta.resource_name,
            'subresource_name': self.attribute,
            'index': obj.pk,
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

        return self._build_reverse_url('api_dispatch_subresource_detail', kwargs=kwargs)
