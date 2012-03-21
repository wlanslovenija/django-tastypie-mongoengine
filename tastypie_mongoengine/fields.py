from tastypie.bundle        import Bundle
from tastypie.resources import Resource
from tastypie.fields        import ApiField

class ListFieldValue(object):
    def __init__(self, value):
        self.value = value

class ListField(ApiField):
    def __init__(self, inner_field, **kwargs):
        super(ListField, self).__init__(**kwargs)

        inner_field.attribute = 'value'
        
        self.inner_field = inner_field
    
    def dehydrate(self, bundle):
        items = getattr(bundle.obj, self.attribute)

        return [self.inner_field.dehydrate(Bundle(obj = ListFieldValue(item))) for item in items]

class DictField(ApiField):
    pass
    
class EmbeddedResourceField(ApiField):
    def __init__(self, resource_type, **kwargs):
        super(EmbeddedResourceField, self).__init__(**kwargs)

        self.resource_type = resource_type
        
    def dehydrate(self, bundle):
            doc = getattr(bundle.obj, self.attribute)

            return self.resource_type().full_dehydrate(doc)