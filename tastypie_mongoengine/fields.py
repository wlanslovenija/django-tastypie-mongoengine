from builtins import object
import tastypie
from tastypie import bundle as tastypie_bundle, exceptions, fields


def link_property(property_name):
    def getter(self):
        return getattr(self, property_name)

    def setter(self, value):
        setattr(self, property_name, value)

    return property(getter, setter)


class ObjectId(fields.ApiField):
    """
    Field for representing ObjectId from MongoDB.
    """

    dehydrated_type = 'objectid'
    help_text = "ID field"


class ApiNameMixin(object):
    def get_api_name(self):
        if getattr(self, 'api_name', None) is not None:
            return self.api_name
        if getattr(self, '_resource', None) and self._resource._meta.api_name is not None:
            return self._resource._meta.api_name
        return None


class GetRelatedMixin(object):
    def get_related_resource(self, related_instance):
        related_resource = super(GetRelatedMixin, self).get_related_resource(related_instance)
        type_map = getattr(related_resource._meta, 'polymorphic', {})
        if type_map and getattr(related_resource._meta, 'prefer_polymorphic_resource_uri', False):
            resource = related_resource._get_resource_from_class(type_map, related_instance.__class__)
            if related_resource.get_resource_uri():
                related_resource._meta.resource_name = resource._meta.resource_name
        return related_resource


class TastypieMongoengineMixin(ApiNameMixin, GetRelatedMixin):
    pass


class BuildRelatedMixin(TastypieMongoengineMixin):
    def build_related_resource(self, value, **kwargs):
        # A version of build_related_resource which allows only dictionary-like data
        if hasattr(value, 'items'):
            self.fk_resource = self.to_class(self.get_api_name())
            # We force resource to cannot be updated so that
            # it is just constructed by resource_from_data
            self.fk_resource.can_update = lambda: False
            return self.resource_from_data(self.fk_resource, value, **kwargs)
        # Or if related object already exists (this happens with PATCH request)
        elif getattr(value, 'obj', None):
            return value
        else:
            raise exceptions.ApiFieldError("The '%s' field was not given a dictionary-alike data: %s." % (self.instance_name, value))


class ReferenceField(TastypieMongoengineMixin, fields.ToOneField):
    """
    References another MongoEngine document.
    """

    dehydrated_type = 'reference'

    def __init__(self, *args, **kwargs):
        help_text = kwargs.pop('help_text', None)

        super(ReferenceField, self).__init__(*args, **kwargs)

        self._help_text = help_text

    @property
    def help_text(self):
        if not self._help_text:
            self._help_text = "Referenced document (%s). Can be either a URI or nested document data." % (self.to_class(self.get_api_name())._meta.resource_name,)
        return self._help_text

    def build_schema(self):
        resource = self.to_class(self.get_api_name())
        return {
            'reference_uri': resource.get_resource_uri(),
            'reference_schema': resource._build_reverse_url('api_get_schema', kwargs={
                'api_name': self.get_api_name(),
                'resource_name': resource._meta.resource_name,
            }),
        }


class EmbeddedDocumentField(BuildRelatedMixin, fields.ToOneField):
    """
    Embeds a resource inside another resource just like you would in MongoEngine.
    """

    is_related = False
    dehydrated_type = 'embedded'

    def __init__(self, embedded, attribute, default=fields.NOT_PROVIDED, null=False, blank=False, readonly=False, help_text=None):
        '''
        The ``embedded`` argument should point to a ``Resource`` class, not
        to a ``document``. Required.
        '''

        super(EmbeddedDocumentField, self).__init__(
            to=embedded,
            attribute=attribute,
            default=default,
            null=null,
            blank=blank,
            readonly=readonly,
            full=True,
        )

        self._help_text = help_text

    @property
    def help_text(self):
        if not self._help_text:
            self._help_text = "Embedded document (%s)." % (self.to_class(self.get_api_name())._meta.resource_name,)
        return self._help_text

    def build_schema(self):
        return {
            'embedded': {
                'fields': self.to_class(self.get_api_name()).build_schema()['fields'],
            },
        }

    def hydrate(self, bundle):
        bundle = super(EmbeddedDocumentField, self).hydrate(bundle)
        if not bundle:
            return bundle
        return bundle.obj


class EmbeddedListField(BuildRelatedMixin, fields.ToManyField):
    """
    Represents a list of embedded objects. It must be used in conjunction
    with EmbeddedDocumentField.
    """

    is_related = False
    is_m2m = False

    def __init__(self, of, attribute, **kwargs):
        self._to_class_with_listresource = None

        help_text = kwargs.pop('help_text', None)

        super(EmbeddedListField, self).__init__(to=of, attribute=attribute, **kwargs)

        self._help_text = help_text

    @property
    def help_text(self):
        if not self._help_text:
            self._help_text = "List of embedded documents (%s)." % (self.to_class(self.get_api_name())._meta.resource_name,)
        return self._help_text

    def build_schema(self):
        data = {
            'embedded': {
                'fields': self.to_class(self.get_api_name()).build_schema()['fields'],
            },
            'related_type': 'to_many',
        }

        type_map = getattr(self.to_class(self.get_api_name())._meta, 'polymorphic', {})
        if not type_map:
            return data

        data['embedded'].update({
            'resource_types': list(type_map.keys()),
        })

        return data

    def dehydrate(self, bundle, for_list=True):
        assert bundle.obj

        the_m2ms = None

        if isinstance(self.attribute, basestring):
            the_m2ms = getattr(bundle.obj, self.attribute)
        elif callable(self.attribute):
            the_m2ms = self.attribute(bundle)

        if not the_m2ms:
            if not self.null:
                raise exceptions.ApiFieldError("The document %r has an empty attribute '%s' and does not allow a null value." % (bundle.obj, self.attribute))
            return []

        self.m2m_resources = []
        m2m_dehydrated = []

        # the_m2ms is a list, not a queryset
        for index, m2m in enumerate(the_m2ms):
            m2m.parent = bundle.obj
            m2m_resource = self.get_related_resource(m2m)

            pk_field = getattr(m2m_resource._meta, 'id_field', None)
            if pk_field is None:
                m2m.pk = index
            else:
                m2m.__class__.pk = link_property(pk_field)

            m2m_bundle = tastypie_bundle.Bundle(obj=m2m, request=bundle.request)
            self.m2m_resources.append(m2m_resource)
            if tastypie.__version__ >= (0, 9, 15):
                m2m_dehydrated.append(self.dehydrate_related(m2m_bundle, m2m_resource, for_list=for_list))
            else:
                m2m_dehydrated.append(self.dehydrate_related(m2m_bundle, m2m_resource))

        return m2m_dehydrated

    def hydrate(self, bundle):
        return [b.obj for b in self.hydrate_m2m(bundle)]

    @property
    def to_class(self):
        if not self._to_class_with_listresource:
            # Importing here to prevent import cycle
            from tastypie_mongoengine import resources
            base = super(EmbeddedListField, self).to_class
            # We create a new ad-hoc resource class here, mixed with MongoEngineListResource, pretending to be original class
            self._to_class_with_listresource = type(base.__name__, (base, resources.MongoEngineListResource), {
                '__module__': base.__module__,
                '_parent': self._resource,
                'attribute': self.attribute or self.instance_name,
            })
        return self._to_class_with_listresource


class ReferencedListField(TastypieMongoengineMixin, fields.ToManyField):
    """
    Represents a list of referenced objects. It must be used in conjunction
    with ReferenceField.
    """

    def __init__(self, of, attribute, **kwargs):
        help_text = kwargs.pop('help_text', None)

        super(ReferencedListField, self).__init__(to=of, attribute=attribute, **kwargs)

        self._help_text = help_text

    @property
    def help_text(self):
        if not self._help_text:
            self._help_text = "List of referenced documents (%s)." % (self.to_class(self.get_api_name())._meta.resource_name,)
        return self._help_text

    def build_schema(self):
        resource = self.to_class(self.get_api_name())
        return {
            'reference_uri': resource.get_resource_uri(),
            'reference_schema': resource._build_reverse_url('api_get_schema', kwargs={
                'api_name': self.get_api_name(),
                'resource_name': resource._meta.resource_name,
            }),
            'related_type': 'to_many',
        }

    def dehydrate(self, bundle, for_list=True):
        if not bundle.obj or not bundle.obj.pk:
            if not self.null:
                raise exceptions.ApiFieldError("The document %r does not have a primary key and can not be used in a ReferencedList context." % bundle.obj)

            return []

        the_m2ms = None

        if isinstance(self.attribute, basestring):
            the_m2ms = getattr(bundle.obj, self.attribute)
        elif callable(self.attribute):
            the_m2ms = self.attribute(bundle)

        if not the_m2ms:
            if not self.null:
                raise exceptions.ApiFieldError("The document %r has an empty attribute '%s' and does not allow a null value." % (bundle.obj, self.attribute))
            return []

        self.m2m_resources = []
        m2m_dehydrated = []

        # the_m2ms is a list, not a queryset
        for m2m in the_m2ms:
            m2m_resource = self.get_related_resource(m2m)
            m2m_bundle = tastypie_bundle.Bundle(obj=m2m, request=bundle.request)
            self.m2m_resources.append(m2m_resource)
            if tastypie.__version__ >= (0, 9, 15):
                m2m_dehydrated.append(self.dehydrate_related(m2m_bundle, m2m_resource, for_list=for_list))
            else:
                m2m_dehydrated.append(self.dehydrate_related(m2m_bundle, m2m_resource))

        return m2m_dehydrated

    def resource_from_data(self, fk_resource, data, request=None, related_obj=None, related_name=None):
        # We are ignoring any extra fields not present in resource
        # We delete them because otherwise resource_from_data fail
        # when using getattr and they are missing in resource
        for k in list(data.keys()):
            if not hasattr(fk_resource, k):
                del data[k]

        return super(ReferencedListField, self).resource_from_data(fk_resource, data, request, related_obj, related_name)
