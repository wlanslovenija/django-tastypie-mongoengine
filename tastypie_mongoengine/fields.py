from tastypie import fields
from tastypie.fields import (ApiField, 
                             ToOneField, 
                             ToManyField, 
                             ApiFieldError,
                             NOT_PROVIDED,)
from tastypie.bundle import Bundle
from tastypie.utils import dict_strip_unicode_keys

class ObjectId(ApiField):
    def __init__(self, **kwargs):
        super(ObjectId, self).__init__(**kwargs)
        
        self.readonly = True
        self.unique = True
        self.blank = False
        self.null = False
        self.help_text = "Id Field"

class ListField(ApiField):
    """
        Represents a list of simple items - strings, ints, bools, etc. For
        embedding objects use EmbeddedListField in combination with EmbeddedDocumentField
        instead.
    """
    dehydrated_type     =   'list'

    def dehydrate(self, obj):
        return self.convert(super(ListField, self).dehydrate(obj))

    def convert(self, value):
        if value is None:
            return None
        return value 

class DictField(ApiField):
    dehydrated_type     =   'dict'
    
    def dehydrate(self, obj):
        return self.convert(super(DictField, self).dehydrate(obj))

    def convert(self, value):
        if value is None:
            return None

        return value

class EmbeddedDocumentField(ToOneField):
    """
        Embeds a resource inside another resource just like you would in Mongo.
    """
    is_related = False
    dehydrated_type     =   'embedded'
    help_text = 'A single related resource. A set of nested resource data.'

    def __init__(self, embedded, attribute, null=False, help_text=None):
        '''
            The ``embedded`` argument should point to a ``Resource`` class, NOT
            to a ``document``. Required.
        '''
        super(EmbeddedDocumentField, self).__init__(
                                                 to=embedded,
                                                 attribute=attribute,
                                                 null=null,
                                                 full=True,
                                                 help_text=help_text,
                                                )
    def dehydrate(self, obj):
        out = super(EmbeddedDocumentField, self).dehydrate(obj).data
        del out["resource_uri"]
        return out

    def hydrate(self, bundle):
        return super(EmbeddedDocumentField, self).hydrate(bundle).obj

    def build_related_resource(self, value):
        """
        Used to ``hydrate`` the data provided. If just a URL is provided,
        the related resource is attempted to be loaded. If a
        dictionary-like structure is provided, a fresh resource is
        created.
        """
        self.fk_resource = self.to_class()
        
        # Try to hydrate the data provided.
        value = dict_strip_unicode_keys(value)
        self.fk_bundle = Bundle(data=value)
            
        return self.fk_resource.full_hydrate(self.fk_bundle)


class EmbeddedListField(ToManyField):
    """
        Represents a list of embedded objects. It must be used in conjunction
        with EmbeddedDocumentField.
        Does not allow for manipulation (reordering) of List elements. Use
        EmbeddedSortedList instead.
    """
    is_related = False
    is_m2m = False

    def __init__(self, of, attribute, related_name=None, default=NOT_PROVIDED, null=False, blank=False, readonly=False, full=False, unique=False, help_text=None):
        super(EmbeddedListField, self).__init__(to=of, 
                                                 attribute=attribute,
                                                 related_name=related_name,
                                                 # default=default, 
                                                 null=null, 
                                                 # blank=blank, 
                                                 # readonly=readonly, 
                                                 full=full, 
                                                 unique=unique, 
                                                 help_text=help_text)
    def dehydrate(self, bundle):
        if not bundle.obj or not bundle.obj.pk:
            if not self.null:
                raise ApiFieldError("The document '%r' does not have a primary key and can not be d in a ToMany context." % bundle.obj)
            return []
        if not getattr(bundle.obj, self.attribute):
            if not self.null:
                raise ApiFieldError("The document '%r' has an empty attribute '%s' and doesn't all a null value." % (bundle.obj, self.attribute))
            return []
        self.m2m_resources = []
        m2m_dehydrated = []
        
        for m2m in getattr(bundle.obj, self.attribute):
            m2m_resource = self.get_related_resource(m2m)
            m2m_bundle = Bundle(obj=m2m)
            self.m2m_resources.append(m2m_resource)
            m2m_dehydrated.append(self.dehydrate_related(m2m_bundle, m2m_resource))
        return m2m_dehydrated

    def hydrate(self, bundle):
        return [b.obj for b in self.hydrate_m2m(bundle)]


class EmbeddedSortedListField(EmbeddedListField):
    """
        EmbeddedSortedListField allows for operating on the sub resources
        individually, through the index based collection.
    """

    def dehydrate(self, bundle):
        if not bundle.obj or not bundle.obj.pk:
            if not self.null:
                raise ApiFieldError("The document '%r' does not have a primary key and can not be d in a ToMany context." % bundle.obj)
            return []
        if not getattr(bundle.obj, self.attribute):
            if not self.null:
                raise ApiFieldError("The document '%r' has an empty attribute '%s' and doesn't all a null value." % (bundle.obj, self.attribute))
            return []
        self.m2m_resources = []
        m2m_dehydrated = []
        
        for index, m2m in enumerate(getattr(bundle.obj, self.attribute)):
            m2m.pk = index
            m2m.parent = bundle.obj
            m2m_resource = self.get_related_resource(m2m)
            m2m_bundle = Bundle(obj=m2m)
            self.m2m_resources.append(m2m_resource)
            m2m_dehydrated.append(self.dehydrate_related(m2m_bundle, m2m_resource))
        return m2m_dehydrated
    
    @property
    def to_class(self):
        base = super(EmbeddedSortedListField, self).to_class
        return lambda: base(self._resource(), self.instance_name)
    