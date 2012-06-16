import mongoengine

class Person(mongoengine.Document):
    meta = {
        'allow_inheritance': True,
    }

    name = mongoengine.StringField(max_length=200, required=True)
    optional = mongoengine.StringField(max_length=200, required=False)

class StrangePerson(Person):
    strange = mongoengine.StringField(max_length=100, required=True)

class EmbeddedPerson(mongoengine.EmbeddedDocument):
    name = mongoengine.StringField(max_length=200, required=True)
    optional = mongoengine.StringField(max_length=200, required=False)

class EmbeddedStrangePerson(EmbeddedPerson):
    strange = mongoengine.StringField(max_length=100, required=True)

class Customer(mongoengine.Document):
    person = mongoengine.ReferenceField(Person)

class EmbeddedComment(mongoengine.EmbeddedDocument):
    content = mongoengine.StringField(max_length=200, required=True)

class EmbeddedPost(mongoengine.EmbeddedDocument):
    title = mongoengine.StringField(max_length=200, required=True)
    comments = mongoengine.ListField(mongoengine.EmbeddedDocumentField(EmbeddedComment))

class Board(mongoengine.Document):
    posts = mongoengine.ListField(mongoengine.EmbeddedDocumentField(EmbeddedPost))

class EmbeddedListInEmbeddedDocTest(mongoengine.Document):
    post = mongoengine.EmbeddedDocumentField(EmbeddedPost)

class EmbeddedDocumentFieldTest(mongoengine.Document):
    customer = mongoengine.EmbeddedDocumentField(EmbeddedPerson)

class DictFieldTest(mongoengine.Document):
    dictionary = mongoengine.DictField(required=True)

class ListFieldTest(mongoengine.Document):
    stringlist = mongoengine.ListField(mongoengine.StringField())
    intlist = mongoengine.ListField(mongoengine.IntField())
    anytype = mongoengine.ListField()

class EmbeddedListFieldTest(mongoengine.Document):
    embeddedlist = mongoengine.ListField(mongoengine.EmbeddedDocumentField(EmbeddedPerson))

class BooleanMapTest(mongoengine.Document):
    is_published_auto = mongoengine.BooleanField(default=False, required=True)
    is_published_defined = mongoengine.BooleanField(default=False, required=True)

class EmbeddedListWithFlagFieldTest(mongoengine.Document):
    embeddedlist = mongoengine.ListField(mongoengine.EmbeddedDocumentField(EmbeddedPerson))
    is_published = mongoengine.BooleanField(default=False, required=True)
