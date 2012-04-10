from tastypie import fields, bundle, utils

class ObjectId(fields.ApiField):
    """
    Field for representing ObjectId from MongoDB.
    """
    
    help_text = "ID field"
    
    def __init__(self, *args, **kwargs):
        super(ObjectId, self).__init__(*args, **kwargs)
        
        self.readonly = True
        self.unique = True
        self.blank = False
        self.null = False

class EmbeddedDocumentField(fields.ToOneField):
    """
    Embeds a resource inside another resource just like you would in MongoDB.
    """
    
    is_related = False
    dehydrated_type = 'embedded'
    help_text = "A single related resource. A set of nested resource data."

    def __init__(self, embedded, attribute, null=False, help_text=None):
        '''
        The ``embedded`` argument should point to a ``Resource`` class, not
        to a ``document``. Required.
        '''
        
        super(EmbeddedDocumentField, self).__init__(
            to=embedded,
            attribute=attribute,
            null=null,
            full=True,
            help_text=help_text,
        )

    def hydrate(self, bundle):
        return super(EmbeddedDocumentField, self).hydrate(bundle).obj

    def build_related_resource(self, value, **kwargs):
        """
        Used to ``hydrate`` the data provided. If just a URL is provided,
        the related resource is attempted to be loaded. If a
        dictionary-like structure is provided, a fresh resource is
        created.
        """
        
        self.fk_resource = self.to_class()
        
        # Try to hydrate the data provided.
        value = utils.dict_strip_unicode_keys(value)
        self.fk_bundle = bundle.Bundle(data=value)
            
        return self.fk_resource.full_hydrate(self.fk_bundle)

class EmbeddedListField(fields.ToManyField):
    """
    Represents a list of embedded objects. It must be used in conjunction
    with EmbeddedDocumentField.
    
    Does not allow for manipulation (reordering) of List elements. Use
    EmbeddedSortedListField instead.
    """
    
    is_related = False
    is_m2m = False

    def __init__(self, of, attribute, **kwargs):
        super(EmbeddedListField, self).__init__(to=of, attribute=attribute, **kwargs)
    
    def dehydrate(self, bundle):
        if not bundle.obj or not bundle.obj.pk:
            if not self.null:
                raise ApiFieldError("The document %r does not have a primary key and can not be in a ToMany context." % bundle.obj)
            return []
        if not getattr(bundle.obj, self.attribute):
            if not self.null:
                raise ApiFieldError("The document %r has an empty attribute '%s' and does not allow a null value." % (bundle.obj, self.attribute))
            return []
        self.m2m_resources = []
        m2m_dehydrated = []
        
        for m2m in getattr(bundle.obj, self.attribute):
            m2m_resource = self.get_related_resource(m2m)
            m2m_bundle = bundle.Bundle(obj=m2m)
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
                raise ApiFieldError("The document %r does not have a primary key and can not be in a ToMany context." % bundle.obj)
            return []
        if not getattr(bundle.obj, self.attribute):
            if not self.null:
                raise ApiFieldError("The document %r has an empty attribute '%s' and does not allow a null value." % (bundle.obj, self.attribute))
            return []
        self.m2m_resources = []
        m2m_dehydrated = []
        
        for index, m2m in enumerate(getattr(bundle.obj, self.attribute)):
            m2m.pk = index
            m2m.parent = bundle.obj
            m2m_resource = self.get_related_resource(m2m)
            m2m_bundle = bundle.Bundle(obj=m2m)
            self.m2m_resources.append(m2m_resource)
            m2m_dehydrated.append(self.dehydrate_related(m2m_bundle, m2m_resource))
            
        return m2m_dehydrated
    
    @property
    def to_class(self):
        base = super(EmbeddedSortedListField, self).to_class
        return lambda: base(self._resource(), self.instance_name)